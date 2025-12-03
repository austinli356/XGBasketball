// src/types.ts

export interface Team {
  name: string;
  abbreviation: string;
  score: number;
  color: string;
  winProb: number;
}

export interface Game {
  id: string; // 
  homeTeam: Team;
  visitorTeam: Team;
  gameStatusText: string;  
  timeLeft: string;
  isLive: boolean;
}