export interface Player {
  id: string;
  name: string;
  color: string;
  score?: number;
}

export interface RoomI {
  id: string;
  hostId: string;
  option: 'asc' | 'desc';
  status: 'lobby' | 'playing' | 'finished';
  players: Record<string, Player>;
  bubbles: Record<string, string>; // bubbleId -> playerId
}