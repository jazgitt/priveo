import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ToastProvider } from '../components';
import { HoursEditor } from './crew/HoursEditor';
import { PasswordDialog, ReleasedJobs } from './crew/shared';
import { AddonsPage } from './addons/AddonsPage';
import { CustomerDetailPage } from './customers/CustomersPage';
import { ScheduleActions } from './schedule/ScheduleActions';
import type { Board } from './schedule/api';
import type { DayHours } from './crew/api';
import { ExceptionsPanel, HoursPanel } from './crew/panels';
import { defaultHours, type Crew } from './crew/api';
import { OptionsManager } from './feedback/OptionsManager';

const fetchMock=vi.fn(); let clients:QueryClient[]=[];
const response=(body:unknown)=>new Response(JSON.stringify(body),{status:200});
let data:Record<string,unknown>;
function mount(ui:React.ReactElement,path='/') {
  const c=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});clients.push(c);
  render(<QueryClientProvider client={c}><ToastProvider><MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter></ToastProvider></QueryClientProvider>);
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

it('books standalone Spa and sends all request filters to the API',async()=>{
  data['/v1/admin/directory/societies']=[{id:'s1',name:'Lake'}];
  data['/v1/admin/customers?q=']=[{id:'c1',name:'Asha'}];
  data['/v1/admin/customers/c1']={vehicles:[{id:'v1',registration:'HR01',society:'Lake',subscription:null},{id:'v2',registration:'HR02',society:'Lake',subscription:{status:'Inactive'}}]};
  mount(<AddonsPage/>);await screen.findByRole('option',{name:'Asha'});await userEvent.selectOptions(screen.getByLabelText('Customer'),'c1');
  await screen.findByRole('option',{name:/HR01/});expect(screen.queryByRole('option',{name:/HR02/})).not.toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText('Vehicle'),'v1');fireEvent.change(screen.getByLabelText('Proposed date'),{target:{value:'2026-10-20'}});
  await userEvent.selectOptions(screen.getByLabelText('Finish by'),'13:00');await userEvent.click(screen.getByRole('button',{name:'Request Deep Spa'}));
  await sent('/v1/admin/addons',{vehicle_id:'v1',service:'Deep Spa',date:'2026-10-20',finish_by:'13:00'});
  await userEvent.type(screen.getByLabelText('Find customer'),'Asha');
  await userEvent.selectOptions(screen.getByLabelText('Status filter'),'Scheduled');await userEvent.selectOptions(screen.getByLabelText('Society filter'),'s1');
  fireEvent.change(screen.getByLabelText('From date'),{target:{value:'2026-10-19'}});fireEvent.change(screen.getByLabelText('To date'),{target:{value:'2026-10-21'}});
  await userEvent.selectOptions(screen.getByLabelText('Add-on filter'),'Deep Spa');
  await waitFor(()=>expect(fetchMock.mock.calls.some(([p])=>p.includes('status=Scheduled&society_id=s1&date_from=2026-10-19&date_to=2026-10-21&service=Deep+Spa'))).toBe(true));
});
it('resolves requested Spa changes, saves a new date and cancels a booking',async()=>{
  data['/v1/admin/addons?']=[{id:'b1',service:'Deep Spa',customer_name:'Asha',vehicle:'HR01',society:'Lake',date:'2026-10-20',finish_by:'12:00',status:'Scheduled',standalone:false,price_rupees:1500,payment_status:'Due',payment_id:'p1',crew_name:'Raj',start_time:'10:00',change_requested:true,requested_date:'2026-10-21',requested_finish_by:'13:00'}];
  mount(<AddonsPage/>);await userEvent.click(await screen.findByRole('button',{name:'Apply requested change'}));await sent('/v1/admin/addons/b1',{resolve_change:true},'PATCH');
  await userEvent.click(screen.getByRole('button',{name:'Reject requested change'}));await sent('/v1/admin/addons/b1',{reject_change:true},'PATCH');
  fireEvent.change(screen.getByLabelText('Service date'),{target:{value:'2026-10-22'}});
  await userEvent.click(screen.getByRole('button',{name:'Save date and time'}));await sent('/v1/admin/addons/b1',{date:'2026-10-22',finish_by:'12:00'},'PATCH');
  await userEvent.click(screen.getByRole('button',{name:'Cancel booking'}));await sent('/v1/admin/addons/b1',{status:'Cancelled'},'PATCH');
  expect(screen.getByRole('link',{name:'Open payment'})).toHaveAttribute('href','/payments?payment=p1');
});

it('swaps jobs and applies selected scheduling improvements with the preview fingerprint',async()=>{
  const refresh=vi.fn();const board={schedule:{id:'s1',status:'Draft'},crew:[{id:'c1',name:'Raj'}],jobs:[{id:'j1',status:'Scheduled',crew_id:'c1',registration:'HR01',service:'Deep Spa',date:'2026-10-20'},{id:'j2',status:'Scheduled',crew_id:'c1',registration:'HR02',service:'Cleaning-External',date:'2026-10-20'}]} as Board;
  data['/v1/admin/scheduling/cutoff-requests']=[{id:'r1',registration:'HR01',customer_name:'Asha',date:'2026-10-20',cutoff_time:'08:00',old_cutoff:null,crew_name:'Raj',start_time:'07:00'}];
  data['/v1/admin/scheduling/needs-scheduling']={pending_addons:[{id:'b1',registration:'HR03',date:'2026-10-21',finish_by:'12:00'}]};
  data['/v1/admin/scheduling/schedules/s1/suggestions']={fingerprint:'version1',items:[{job_id:'j1',crew_id:'c1',start_minute:425,date:'2026-10-20',service:'Deep Spa'}]};
  mount(<ScheduleActions board={board} refresh={refresh}/>);
  await userEvent.click(await screen.findByRole('button',{name:'Apply and schedule'}));await sent('/v1/admin/scheduling/cutoff-requests/r1/handle',{apply:true});
  await userEvent.click(screen.getByRole('button',{name:'Reject'}));await sent('/v1/admin/scheduling/cutoff-requests/r1/handle',{apply:false});
  await userEvent.selectOptions(screen.getByLabelText('First job'),'j1');await userEvent.selectOptions(screen.getByLabelText('Second job'),'j2');
  await userEvent.click(screen.getByRole('button',{name:'Swap crew and times'}));await sent('/v1/admin/scheduling/jobs/swap',{first_job_id:'j1',second_job_id:'j2'});
  await userEvent.click(screen.getByRole('button',{name:'Preview improvements'}));const choice=await screen.findByRole('checkbox');
  await userEvent.click(choice);await userEvent.click(choice);expect(screen.getByRole('button',{name:'Apply selected improvements'})).toBeDisabled();
  await userEvent.click(choice);await userEvent.click(screen.getByRole('button',{name:'Apply selected improvements'}));
  await sent('/v1/admin/scheduling/schedules/s1/suggestions/apply',{fingerprint:'version1',job_ids:['j1']});expect(refresh).toHaveBeenCalled();
});
it('disables draft actions on a frozen schedule',async()=>{
  data['/v1/admin/scheduling/needs-scheduling']={pending_addons:[]};
  mount(<ScheduleActions board={{schedule:{id:'s1',status:'Frozen'},jobs:[],crew:[]} as unknown as Board} refresh={()=>{}}/>);
  expect(screen.getByRole('button',{name:'Preview improvements'})).toBeDisabled();expect(await screen.findByText('No pending cutoff requests.')).toBeInTheDocument();
});

it('edits customer details, credentials, notifications and signed-in sessions',async()=>{
  const c={id:'c1',first_name:'Asha',last_name:'Rao',mobile:'9876543210',email:'asha@example.com',flat:'A1',email_verified:true,password_set:true,onboarding_confirmed:true,vehicles:[]};
  data['/v1/admin/customers/c1']=c;
  data['/v1/admin/customers/c1/sessions']=[{id:'t1',device_name:'Phone',platform:'Android',app_version:'1',last_active:'2026-10-13T10:00:00Z',channel:'mobile'}];
  data['/v1/admin/customers/c1/notification-preferences']={items:[{event:'payment_due',label:'Payments',enabled:true}]};
  mount(<Routes><Route path='/customers/:id' element={<CustomerDetailPage/>}/></Routes>,'/customers/c1');
  await screen.findByLabelText('First name');await userEvent.clear(screen.getByLabelText('First name'));await userEvent.type(screen.getByLabelText('First name'),'Ash');
  await userEvent.click(screen.getByRole('button',{name:'Save customer'}));await sent('/v1/admin/customers/c1',{first_name:'Ash',last_name:'Rao',mobile:'9876543210',flat:'A1'},'PATCH');
  await userEvent.click(screen.getByRole('button',{name:'Resend welcome email'}));await sent('/v1/admin/customers/c1/resend-welcome');
  await userEvent.click(screen.getByText('Email and password reset'));await userEvent.clear(screen.getByLabelText('Correct email'));await userEvent.type(screen.getByLabelText('Correct email'),'new@example.com');
  await userEvent.click(screen.getByRole('button',{name:'Correct email'}));await sent('/v1/admin/customers/c1/email',{email:'new@example.com'},'PATCH');
  await userEvent.click(screen.getByRole('button',{name:'Clear password'}));await sent('/v1/admin/customers/c1/reset-password');
  await userEvent.click(screen.getByLabelText('Payments'));await sent('/v1/admin/customers/c1/notification-preferences',{items:[{event:'payment_due',enabled:false}]},'PUT');
  await userEvent.click(screen.getByRole('button',{name:'Sign out session'}));await sent('/v1/admin/customers/c1/sessions/t1/logout');
  await userEvent.click(screen.getByRole('button',{name:'Sign out all sessions'}));await sent('/v1/admin/customers/c1/sessions/logout');
});

it('saves crew hours and creates, edits and removes late-start exceptions',async()=>{
  const crew={id:'c1',name:'Raj',working_hours:defaultHours(),exceptions:[{id:'e1',date:'2026-10-20',kind:'Late start',start:'08:00'}]} as Crew;
  fetchMock.mockImplementation(async (_p:string,o?:RequestInit)=>response(o?.method ? {released_jobs:[{job_id:'j1',date:'2026-10-20',service:'Deep Spa',registration:'HR01'}]} : []));
  mount(<><HoursPanel crew={crew}/><ExceptionsPanel crew={crew}/></>);
  await userEvent.click(screen.getByRole('button',{name:'Save working hours'}));
  expect(await screen.findByText('Working hours saved.')).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText('Type'),'Late start');
  fireEvent.change(screen.getByLabelText('From date'),{target:{value:'2026-10-21'}});
  fireEvent.change(screen.getByLabelText('To date'),{target:{value:'2026-10-22'}});
  fireEvent.change(screen.getByLabelText('Can start at'),{target:{value:'09:00'}});
  await userEvent.click(screen.getByRole('button',{name:'Add exception'}));
  await sent('/v1/admin/crew/c1/exceptions',{kind:'Late start',from_date:'2026-10-21',to_date:'2026-10-22',start:'09:00'});
  await userEvent.click(screen.getByRole('button',{name:'Edit 2026-10-20'}));
  await userEvent.selectOptions(screen.getByLabelText('Edit type'),'Leave');
  await userEvent.click(screen.getByRole('button',{name:'Save'}));
  await sent('/v1/admin/crew/c1/exceptions/e1',{kind:'Leave',start:''},'PATCH');
  await userEvent.click(screen.getByRole('button',{name:'Remove 2026-10-20'}));
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
  await userEvent.click(screen.getByRole('button',{name:'Deactivate'}));await sent('/v1/admin/support/options/o1',{active:false},'PATCH');
  await userEvent.selectOptions(screen.getByLabelText('List'),'checkin_category');await userEvent.type(screen.getByLabelText('New name'),'Quality');await userEvent.type(screen.getByLabelText('New description'),'Monthly quality');
  await userEvent.click(screen.getByRole('button',{name:'Add'}));await sent('/v1/admin/support/options',{kind:'checkin_category',name:'Quality',description:'Monthly quality'});
});
