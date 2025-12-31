// src/types.ts

export interface Team {
  name: string;
  abbreviation: string;
  score: number;
  color: string;
  winProb: number | null;
}

export interface Game {
  id: string; // 
  homeTeam: Team;
  visitorTeam: Team;
  gameStatusText: string; 
  gameState: number; 
  timeLeft: string;
  lastPlay: string;

}