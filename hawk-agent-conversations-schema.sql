-- HAWK Agent Conversations Table Schema
-- This table stores conversational interactions for Agent Mode

create table if not exists public.hawk_agent_conversations (
  id bigserial primary key,
  conversation_id text not null unique,
  user_id text not null default 'test-user',
  title text not null,
  messages jsonb not null default '[]'::jsonb,
  message_count int not null default 0,
  status text not null default 'active' check (status in ('active', 'archived')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Indexes for performance
create index if not exists idx_hawk_conversations_user_id on public.hawk_agent_conversations (user_id);
create index if not exists idx_hawk_conversations_status on public.hawk_agent_conversations (status);
create index if not exists idx_hawk_conversations_updated_at on public.hawk_agent_conversations (updated_at desc);
create index if not exists idx_hawk_conversations_conversation_id on public.hawk_agent_conversations (conversation_id);

-- Trigger for updated_at
drop trigger if exists tr_hawk_conversations_updated_at on public.hawk_agent_conversations;
create trigger tr_hawk_conversations_updated_at
before update on public.hawk_agent_conversations
for each row execute function public.set_timestamp_updated_at();

-- Row Level Security
alter table public.hawk_agent_conversations enable row level security;

do $$ begin
  if not exists (select 1 from pg_policies where tablename='hawk_agent_conversations' and policyname='allow_rw_conversations') then
    create policy allow_rw_conversations on public.hawk_agent_conversations for all using (true) with check (true);
  end if;
end $$;

comment on table public.hawk_agent_conversations is 'Agent Mode conversations with message history';