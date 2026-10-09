export type Tick = number

declare module 'claude-code' {
  interface PluginState {
    'priveo-reqs': { tick: Tick }
  }
}
