import { useState } from 'react';
import { withSite } from "../site/testSite";
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ToastProvider } from '../components';
import { choose, confirmWith, PortalProviders } from '../test/portal';
import { HoursEditor } from './crew/HoursEditor';
import { PasswordDialog, ReleasedJobs } from './crew/shared';
import type { DayHours } from './crew/api';
import { ExceptionsPanel, HoursPanel } from './crew/panels';
import { defaultHours, type Crew } from './crew/api';
import { OptionsManager } from './feedback/OptionsManager';

const fetchMock=vi.fn(); let clients:QueryClient[]=[];
const response=(body:unknown)=>new Response(JSON.stringify(body),{status:200});
let data:Record<string,unknown>;
function mount(ui:React.ReactElement,path='/') {
  const c=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});clients.push(c);
  render(<QueryClientProvider client={c}><ToastProvider><MemoryRouter initialEntries={[path]}><PortalProviders>{withSite(ui)}</PortalProviders></MemoryRouter></ToastProvider></QueryClientProvider>);
}
async function sent(path:string,body?:unknown,method='POST') {
  await waitFor(()=>expect(fetchMock.mock.calls.some(([p,o])=>p===path && o?.method===method && (body===undefined || JSON.stringify(JSON.parse(o.body))===JSON.stringify(body)))).toBe(true));
}
beforeEach(()=>{
  clients=[];data={};fetchMock.mockReset();
  fetchMock.mockImplementation(async (p:string,o?:RequestInit)=>response(data[p] ?? (o?.method && o.method!=='GET'? {}:[])));
  vi.stubGlobal('fetch',fetchMock);
});
afterEach(()=>{clients.forEach(c=>c.clear());vi.unstubAllGlobals();});

it('working hours changes preserve the other days and show validation',async()=>{
  const onChange=vi.fn();
  function Editor(){const [hours,set]=useState<DayHours[]>([]);return <HoursEditor value={hours} error='End must follow start' onChange={v=>{set(v);onChange(v);}}/>;}
  mount(<Editor/>); expect(screen.getByRole('alert')).toHaveTextContent('End must follow start');
  await userEvent.click(screen.getByLabelText('Monday working'));
  expect(onChange.mock.calls.at(-1)![0][0]).toMatchObject({day:'Monday',working:true,start:'06:00',end:'12:00'});
  fireEvent.change(screen.getByLabelText('Monday start'),{target:{value:'07:00'}});
  fireEvent.change(screen.getByLabelText('Monday end'),{target:{value:'13:00'}});
  expect(onChange.mock.calls.at(-1)![0][0]).toMatchObject({start:'07:00',end:'13:00'});
  await userEvent.click(screen.getByLabelText('Monday working')); expect(screen.queryByLabelText('Monday start')).not.toBeInTheDocument();
  await userEvent.click(screen.getByLabelText('Monday working')); expect(screen.getByLabelText('Monday start')).toHaveValue('07:00');
});
it('copies a one-time crew password and closes only after acknowledgement',async()=>{
  const user=userEvent.setup();const copy=vi.spyOn(navigator.clipboard,'writeText').mockResolvedValue();const done=vi.fn();
  mount(<PasswordDialog issued={{login_id:'9000000001',password:'Unit-Test!',crew:{name:'Raj'}} as never} onDone={done}/>);
  await user.click(screen.getByRole('button',{name:'Copy'}));
  expect(copy).toHaveBeenCalledWith('Login ID: 9000000001\nPassword: Unit-Test!');
  expect(screen.getByRole('button',{name:'Copied'})).toBeInTheDocument();
  await user.keyboard('{Escape}');expect(done).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button',{name:'I have noted it'}));expect(done).toHaveBeenCalledOnce();copy.mockRestore();
});
it('explains clipboard failures and lists released work',async()=>{
  const user=userEvent.setup();const copy=vi.spyOn(navigator.clipboard,'writeText').mockRejectedValue(new Error('denied'));
  mount(<><PasswordDialog issued={{login_id:'1',password:'Test!',crew:{name:'Raj'}} as never} onDone={()=>{}}/><ReleasedJobs jobs={[{job_id:'j1',vehicle_id:'v1',date:'2026-10-20',service:'Deep Spa',registration:'HR01'}]}/></>);
  await user.click(screen.getByRole('button',{name:'Copy'}));expect(await screen.findByText('Could not copy. Write the password down.')).toBeInTheDocument();
  expect(screen.getByText('1 job went to Needs scheduling.')).toBeInTheDocument();copy.mockRestore();
});

// The Schedule actions and the customer detail page are tested next to their
// pages (schedule/SchedulePage.test.tsx, customers/customers.test.tsx).

it('saves crew hours and creates, edits and removes late-start exceptions',async()=>{
  const crew={id:'c1',name:'Raj',working_hours:defaultHours(),exceptions:[{id:'e1',date:'2026-10-20',kind:'Late start',start:'08:00'}]} as Crew;
  fetchMock.mockImplementation(async (_p:string,o?:RequestInit)=>response(o?.method ? {released_jobs:[{job_id:'j1',date:'2026-10-20',service:'Deep Spa',registration:'HR01'}]} : []));
  mount(<><HoursPanel crew={crew}/><ExceptionsPanel crew={crew}/></>);
  await userEvent.click(screen.getByRole('button',{name:'Save working hours'}));
  expect(await screen.findByText('Working hours saved.')).toBeInTheDocument();
  await choose('Type','Late start');
  fireEvent.change(screen.getByLabelText('From date'),{target:{value:'2026-10-21'}});
  fireEvent.change(screen.getByLabelText('To date'),{target:{value:'2026-10-22'}});
  fireEvent.change(screen.getByLabelText('Can start at'),{target:{value:'09:00'}});
  await userEvent.click(screen.getByRole('button',{name:'Add exception'}));
  await sent('/v1/admin/crew/c1/exceptions',{kind:'Late start',from_date:'2026-10-21',to_date:'2026-10-22',start:'09:00'});
  await userEvent.click(screen.getByRole('button',{name:'Edit 2026-10-20'}));
  await choose('Edit type','Leave');
  await userEvent.click(screen.getByRole('button',{name:'Save'}));
  await sent('/v1/admin/crew/c1/exceptions/e1',{kind:'Leave',start:''},'PATCH');
  await userEvent.click(screen.getByRole('button',{name:'Remove 2026-10-20'}));await confirmWith('Remove');
  await sent('/v1/admin/crew/c1/exceptions/e1',undefined,'DELETE');
});

it('edits, reorders, activates and creates feedback options without changing historical answers',async()=>{
  data['/v1/admin/support/options']=[{id:'o1',kind:'feedback_category',name:'Care',description:'Crew care',sort_order:0,active:true},{id:'o2',kind:'feedback_category',name:'Timing',description:'',sort_order:1,active:false}];
  mount(<OptionsManager/>);await screen.findByText('Care');
  await userEvent.click(screen.getAllByRole('button',{name:'Edit'})[0]);
  await userEvent.clear(screen.getByLabelText('Name'));await userEvent.type(screen.getByLabelText('Name'),'Attention');
  await userEvent.clear(screen.getByLabelText('Description'));await userEvent.type(screen.getByLabelText('Description'),'Detailed care');
  await userEvent.click(screen.getByRole('button',{name:'Save'}));await sent('/v1/admin/support/options/o1',{name:'Attention',description:'Detailed care'},'PATCH');
  await userEvent.click(screen.getAllByRole('button',{name:'Edit'})[0]);await userEvent.click(screen.getByRole('button',{name:'Cancel'}));
  await userEvent.click(screen.getByRole('button',{name:'Move Care down'}));await sent('/v1/admin/support/options/o1',{sort_order:1},'PATCH');
  await userEvent.click(screen.getByRole('button',{name:'Move Timing up'}));await sent('/v1/admin/support/options/o2',{sort_order:0},'PATCH');
  await userEvent.click(screen.getByRole('button',{name:'Activate'}));await sent('/v1/admin/support/options/o2',{active:true},'PATCH');
  await userEvent.click(screen.getByRole('button',{name:'Deactivate'}));await confirmWith('Deactivate');await sent('/v1/admin/support/options/o1',{active:false},'PATCH');
  await choose('List','Check-in categories');await userEvent.type(screen.getByLabelText('New name'),'Quality');await userEvent.type(screen.getByLabelText('New description'),'Monthly quality');
  await userEvent.click(screen.getByRole('button',{name:'Add'}));await sent('/v1/admin/support/options',{kind:'checkin_category',name:'Quality',description:'Monthly quality'});
});
