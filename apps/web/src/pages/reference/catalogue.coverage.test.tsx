import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { ToastProvider } from '../../components';
import { PlansTab } from './PlansTab';
import { AddonsTab } from './AddonsTab';
import { VehiclesTab } from './VehiclesTab';
import { SlotsTab } from './SlotsTab';
import { OrderedList } from './OrderedList';
import { ChecklistsTab } from './ChecklistsTab';

const fetchMock = vi.fn();
let responses: Record<string, unknown>;
let clients: QueryClient[];
function mount(ui: React.ReactElement) {
  const client = new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});
  clients.push(client);
  render(<QueryClientProvider client={client}><ToastProvider>{ui}</ToastProvider></QueryClientProvider>);
}
const calls = (path:string, method:string) => fetchMock.mock.calls.filter(([url,init])=>String(url)==='/v1/admin/directory'+path && (init?.method ?? 'GET')===method);
async function field(label:string,value:string) {
  const input=within(screen.getByRole('dialog')).getByLabelText(label);
  await userEvent.clear(input); if(value) await userEvent.type(input,value);
}
async function saved(path:string, method='POST') {
  await userEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Save'}));
  await waitFor(()=>expect(calls(path,method)).toHaveLength(1));
  await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  return JSON.parse(calls(path,method)[0][1].body);
}
beforeEach(()=>{
  clients=[]; responses={}; fetchMock.mockReset();
  fetchMock.mockImplementation(async (url:string,init?:RequestInit)=>new Response(JSON.stringify(responses[url] ?? ((init?.method ?? 'GET') === 'GET' ? [] : {})),{status:200}));
  vi.stubGlobal('fetch',fetchMock);
});
afterEach(()=>{ clients.forEach(c=>c.clear()); vi.unstubAllGlobals(); });

it('creates a plan with complete pricing and inclusions',async()=>{
  responses['/v1/admin/directory/plans']=[]; mount(<PlansTab/>);
  await userEvent.click(screen.getByRole('button',{name:'Add a plan'}));
  expect(within(screen.getByRole('dialog')).getByRole('button',{name:'Save'})).toBeDisabled();
  await field('Name','Premium'); await field('Monthly price (Rs, GST included)','1600');
  await field('List price (Rs, struck through)','1900'); await field('Badge','Launch');
  await field('Sort order','2'); await field('Inclusions (one per line)','Exterior\nInterior');
  await userEvent.click(screen.getByLabelText('Includes interior care'));
  expect(await saved('/plans')).toEqual({name:'Premium',monthly_price_rupees:1600,list_price_rupees:1900,badge:'Launch',sort_order:2,includes_interior:true,inclusions:['Exterior','Interior']});
});
it('edits a plan and clears the old list price',async()=>{
  responses['/v1/admin/directory/plans']=[{id:'p1',name:'Premium',monthly_price_rupees:1600,list_price_rupees:1900,badge:'Launch',sort_order:0,includes_interior:true,inclusions:['Exterior'],active:true,active_subscriptions:2}];
  mount(<PlansTab/>); await userEvent.click(await screen.findByRole('button',{name:'Edit Premium'}));
  await field('List price (Rs, struck through)','');
  expect(await saved('/plans/p1','PATCH')).toMatchObject({clear_list_price:true});
  await userEvent.click(screen.getByRole('button',{name:'Deactivate Premium'}));
  await waitFor(()=>expect(calls('/plans/p1/deactivate','POST')).toHaveLength(1));
});
it('reactivates a plan and cancels a new draft',async()=>{
  responses['/v1/admin/directory/plans']=[{id:'p1',name:'Basic',monthly_price_rupees:1000,sort_order:0,includes_interior:false,inclusions:[],active:false,active_subscriptions:0}];
  mount(<PlansTab/>); await userEvent.click(await screen.findByRole('button',{name:'Reactivate Basic'}));
  await waitFor(()=>expect(calls('/plans/p1/reactivate','POST')).toHaveLength(1));
  await userEvent.click(screen.getByRole('button',{name:'Add a plan'}));
  await userEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Cancel'}));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
it('creates a priced Spa catalogue item',async()=>{
  responses['/v1/admin/directory/addons']=[]; mount(<AddonsTab/>);
  await userEvent.click(screen.getByRole('button',{name:'Add an add-on'}));
  await field('Name','Spa'); await field('Description','Five step clean');
  await field('Price (Rs, GST included)','1500'); await field('List price (Rs, struck through)','1800');
  await field('Duration (minutes)','120'); await field('Sort order','3');
  expect(await saved('/addons')).toEqual({name:'Spa',description:'Five step clean',price_rupees:1500,list_price_rupees:1800,duration_minutes:120,sort_order:3});
});
it('edits and deactivates a Spa catalogue item',async()=>{
  responses['/v1/admin/directory/addons']=[{id:'a1',name:'Spa',description:'Clean',price_rupees:1500,list_price_rupees:1800,duration_minutes:120,sort_order:0,active:true,service:'Deep Spa'}];
  mount(<AddonsTab/>); await userEvent.click(await screen.findByRole('button',{name:'Edit Spa'}));
  await field('List price (Rs, struck through)',''); await field('Duration (minutes)','');
  expect(await saved('/addons/a1','PATCH')).toMatchObject({clear_list_price:true});
  await userEvent.click(screen.getByRole('button',{name:'Deactivate Spa'}));
  await waitFor(()=>expect(calls('/addons/a1/deactivate','POST')).toHaveLength(1));
});
it('reactivates a catalogue item and cancels its draft',async()=>{
  responses['/v1/admin/directory/addons']=[{id:'a1',name:'Spa',description:'',price_rupees:1500,sort_order:0,active:false,service:'Deep Spa'}];
  mount(<AddonsTab/>); await userEvent.click(await screen.findByRole('button',{name:'Reactivate Spa'}));
  await waitFor(()=>expect(calls('/addons/a1/reactivate','POST')).toHaveLength(1));
  await userEvent.click(screen.getByRole('button',{name:'Add an add-on'}));
  await userEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Cancel'}));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
it('creates, filters, searches and edits vehicle catalogue details',async()=>{
  const vehicles=[{id:'v1',make:'Hyundai',model:'Creta',variant:'SX',category:'SUV',active:true},{id:'v2',make:'Tata',model:'Tiago',variant:'',category:'Hatch',active:false}];
  responses['/v1/admin/directory/vehicle-catalogue']=vehicles;
  responses['/v1/admin/directory/vehicle-catalogue/categories']=['SUV','Hatch'];
  responses['/v1/admin/directory/vehicle-catalogue?q=Creta']=vehicles.slice(0,1);
  mount(<VehiclesTab/>); await screen.findByText('Hyundai');
  await userEvent.selectOptions(screen.getByLabelText('Category'),'SUV'); expect(screen.queryByText('Tata')).not.toBeInTheDocument();
  await userEvent.type(screen.getByLabelText('Search make or model'),'Creta'); await screen.findByText('Hyundai');
  await userEvent.click(screen.getByRole('button',{name:'Edit Hyundai Creta SX'}));
  await field('Make','Hyundai'); await field('Model','Creta'); await field('Variant','EX'); await field('Category','SUV');
  expect(await saved('/vehicle-catalogue/v1','PATCH')).toEqual({make:'Hyundai',model:'Creta',variant:'EX',category:'SUV'});
  await userEvent.click(screen.getByRole('button',{name:'Deactivate Hyundai Creta SX'}));
  await waitFor(()=>expect(calls('/vehicle-catalogue/v1/deactivate','POST')).toHaveLength(1));
  await userEvent.click(screen.getByRole('button',{name:'Add a vehicle'}));
  await field('Make','Kia');await field('Model','Seltos');await field('Category','SUV');
  expect(await saved('/vehicle-catalogue','POST')).toMatchObject({make:'Kia',model:'Seltos',variant:'',category:'SUV'});
});
it('reactivates a vehicle and cancels an edit',async()=>{
  responses['/v1/admin/directory/vehicle-catalogue']=[{id:'v2',make:'Tata',model:'Tiago',variant:'',category:'Hatch',active:false}];
  responses['/v1/admin/directory/vehicle-catalogue/categories']=['Hatch']; mount(<VehiclesTab/>);
  await userEvent.click(await screen.findByRole('button',{name:'Reactivate Tata Tiago'}));
  await waitFor(()=>expect(calls('/vehicle-catalogue/v2/reactivate','POST')).toHaveLength(1));
  await userEvent.click(screen.getByRole('button',{name:'Edit Tata Tiago'}));
  await userEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Cancel'}));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
it('creates, edits and deletes working slots with ordered weekdays',async()=>{
  responses['/v1/admin/directory/societies?include_inactive=false']=[{id:'s1',name:'Lake'},{id:'s2',name:'Park'}];
  const slot={id:'t1',service:'Cleaning-External',start:'05:00',end:'11:00',days:['Monday','Tuesday']};
  responses['/v1/admin/directory/societies/s1/slots?service=Cleaning-External']=[slot];
  responses['/v1/admin/directory/societies/s2/slots?service=Cleaning-External']=[slot];
  mount(<SlotsTab/>); await screen.findByText('05:00 to 11:00');
  await userEvent.selectOptions(screen.getByLabelText('Society'),'s2');
  await userEvent.click(screen.getByRole('button',{name:'Add a slot'}));
  await userEvent.selectOptions(within(screen.getByRole('dialog')).getByLabelText('Service'),'Cleaning-Internal');
  await field('Start (HH:MM)','06:00'); await field('End (HH:MM, 24:00 for midnight)','12:00');
  await userEvent.click(screen.getByLabelText('Sunday')); await userEvent.click(screen.getByLabelText('Sunday'));
  expect(await saved('/societies/s2/slots')).toMatchObject({service:'Cleaning-Internal',start:'06:00',end:'12:00'});
  await userEvent.click(screen.getByRole('button',{name:'Edit'}));
  await userEvent.click(screen.getByLabelText('Tuesday'));
  expect(await saved('/slots/t1','PATCH')).toMatchObject({days:['Monday']});
  await userEvent.click(screen.getByRole('button',{name:'Delete'}));
  await waitFor(()=>expect(calls('/slots/t1','DELETE')).toHaveLength(1));
});
it('disables slot creation without a society',async()=>{
  responses['/v1/admin/directory/societies?include_inactive=false']=[]; mount(<SlotsTab/>);
  expect(await screen.findByText('Add a society first.')).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Add a slot'})).toBeDisabled();
});
it('renames, reorders, activates and adds checklist rows',async()=>{
  mount(<OrderedList rows={[{id:'r1',label:'Vacuum',active:true},{id:'r2',label:'Polish',active:false}]} noun='step' addPath='/steps' orderPath='/steps/order' itemPath='/steps' renameNote='History is preserved.'/>);
  await userEvent.click(screen.getByRole('button',{name:'Rename Vacuum'}));
  await userEvent.clear(screen.getByLabelText('New text for Vacuum')); await userEvent.type(screen.getByLabelText('New text for Vacuum'),'Vacuum seats');
  await userEvent.click(screen.getByRole('button',{name:'Save'}));
  await waitFor(()=>expect(calls('/steps/r1','PATCH')).toHaveLength(1));
  expect(JSON.parse(calls('/steps/r1','PATCH')[0][1].body)).toEqual({label:'Vacuum seats'});
  await userEvent.click(screen.getByRole('button',{name:'Rename Vacuum'})); await userEvent.click(screen.getByRole('button',{name:'Cancel'}));
  await userEvent.click(screen.getByRole('button',{name:'Deactivate Vacuum'})); await userEvent.click(screen.getByRole('button',{name:'Reactivate Polish'}));
  await userEvent.click(screen.getByRole('button',{name:'Move Polish up'}));
  await waitFor(()=>expect(calls('/steps/order','PUT')).toHaveLength(1));
  expect(JSON.parse(calls('/steps/order','PUT')[0][1].body)).toEqual({ids:['r2','r1']});
  await userEvent.click(screen.getByRole('button',{name:'Move Vacuum down'}));
  await userEvent.type(screen.getByLabelText('New step'),'Dry'); await userEvent.click(screen.getByRole('button',{name:'Add step'}));
  const adds = () => fetchMock.mock.calls.filter(([url,init])=>url==='/v1/admin/directory/steps' && init?.method==='POST');
  await waitFor(()=>expect(adds()).toHaveLength(1));
  expect(JSON.parse(adds()[0][1].body)).toEqual({label:'Dry'});
});
it('loads both editable cleaning checklists',async()=>{
  responses['/v1/admin/directory/checklists']=[{service:'Cleaning-Internal',items:[{id:'i1',label:'Vacuum',active:true}]},{service:'Deep Spa',items:[{id:'d1',label:'Foam',active:true}]}];
  mount(<ChecklistsTab/>); await screen.findByText('Vacuum');
  expect(await screen.findByText('Foam')).toBeInTheDocument();
});
