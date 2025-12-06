// src/App.tsx
import React, { useState, useEffect } from 'react';
import type { Game} from './types'; 

const parseClock = (clock: string) => {
  const [min, sec] = clock.split(":").map(Number);
  return min * 60 + sec;
};

const formatClock = (seconds: number) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
};

const getLogoUrl = (text: string) => 
  `/src/logos/${text}.png`;

const GameCard: React.FC<{ game: Game, onCalculate: (game: Game) => void }> = ({ game, onCalculate }) => {
  const [localClock, setLocalClock] = useState(parseClock(game.gameStatusText));
  const areWinProbsCalculated = 
    game.homeTeam.winProb !== null && 
    game.visitorTeam.winProb !== null;
    const showButton = !areWinProbsCalculated && game.gameState!=3;
  // Whenever the API updates gameStatusText, realign the clock
  useEffect(() => {
    setLocalClock(parseClock(game.gameStatusText));
  }, [game.gameStatusText]);

  // Start ticking if game is live
  useEffect(() => {
    if (!game.isLive) return;

    const interval = setInterval(() => {
      setLocalClock((prev) => Math.max(prev - 1, 0));
    }, 1000);

    return () => clearInterval(interval);
  }, [game.isLive]);
  return (
    <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-4">
      {/* Header: Quarter & Time */}
      <div className="bg-gray-50 px-4 py-2 flex justify-between items-center border-b border-gray-100">
        <span className={`text-xs font-bold uppercase tracking-wider ${game.isLive ? 'text-red-600 animate-pulse' : 'text-gray-500'}`}>
          {game.gameState==2 ? '● Live' : (game.gameState==1 ? 'Upcoming' : 'Final')}
        </span>
        <span className="text-sm font-medium text-gray-700">
          {game.gameStatusText}
        </span>
      </div>

      {/* Content: Teams & Scores */}
      <div className="p-5 flex justify-between items-center relative">
        {/* Visitor Team */}
        <div className="flex flex-col items-center w-1/3">
          <img 
            src={getLogoUrl(game.visitorTeam.abbreviation)} 
            alt={game.visitorTeam.name} 
            className="w-25 h-25 object-contain"
          />
          <p className="text-2xl font-black text-gray-900 mt-1">{game.gameState>1 ? game.visitorTeam.score : ""}</p>
        </div>

        {/* VS / Divider */}
        <div className="flex flex-col items-center w-1/3 px-2">
          <span className="text-gray-300 font-bold text-xl italic">VS</span>
        </div>

        {/* Home Team */}
        <div className="flex flex-col items-center w-1/3">
          <img 
            src={getLogoUrl(game.homeTeam.abbreviation)} 
            alt={game.homeTeam.name} 
            className="w-25 h-25 object-contain"
          />
          <p className="text-2xl font-black text-gray-900 mt-1">{game.gameState>2 ? game.homeTeam.score : ""}</p>
        </div>
      </div>
      {game.homeTeam.winProb !== null && game.visitorTeam.winProb !== null && (
          <div className="relative bottom-0 left-0 w-full h-6 flex justify-center rounded-b">           
            {/* <div
              className="bg-blue-500 h-full rounded-l left-0"
              style={{ width: `${game.visitorTeam.winProb/1.2}%` }}
            > */}
            <h3 className="flex justify-center text-red-600 text-sm">
              The model believes the {game.visitorTeam.winProb>game.homeTeam.winProb ? game.visitorTeam.name : game.homeTeam.name} have a {game.visitorTeam.winProb>game.homeTeam.winProb ? game.visitorTeam.winProb : game.homeTeam.winProb}% chance of winning
            </h3>
            {/* </div> */}
            {/* <div
              className="bg-red-500 h-full rounded-r right-0"
              style={{ width: `${game.homeTeam.winProb/1.2}%` }}
            > */}
            {/* <h3 className="flex justify-center font-bold text-black text-sm">W: {game.homeTeam.winProb}%</h3> */}
            {/* </div> */}
          </div>
      )}
      {showButton && <button
        onClick={() => onCalculate(game)}
        className="w-full bg-blue-400 text-white py-2 text-sm font-semibold hover:bg-blue-700"
      >
        Predict Winner
      </button>}
      <div className="px-4 py-2 text-center text-xs text-gray-400 border-t border-gray-50">
        {game.visitorTeam.name} @ {game.homeTeam.name}
      </div>
    </div>
  );
};


const App: React.FC = () => {
  const [liveGames, setLiveGames] = useState<Game[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Function to fetch data from your Python backend
  const fetchLiveScores = async () => {
    try {
      // 1. Call your local Python API endpoint (running on port 5000)
      const response = await fetch('http://localhost:5000/api/nba-scores');

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      // 2. Data is already formatted correctly by Python, so we cast it to Game[]
      const data: Game[] = await response.json();
      setLiveGames((prev) => {
        const existingGamesMap = new Map(prev.map(g => [g.id, g]));

        return data.map((newGame) => {
          const existingGame = existingGamesMap.get(newGame.id);

          if (existingGame && existingGame.homeTeam.winProb !== undefined) {
            return {
              ...newGame,
              homeTeam: { 
                ...newGame.homeTeam, 
                winProb: existingGame.homeTeam.winProb 
              },
              visitorTeam: { 
                ...newGame.visitorTeam, 
                winProb: existingGame.visitorTeam.winProb 
              },
            };
          }
          return newGame;
        });
      });
      setError(null);
    } catch (err) {
      setError("Could not fetch live scores. Is the Python server running?");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };
  const runCalculationsForGame = async (game: Game) => {
    try {
      const response = await fetch("http://localhost:5000/run-calculations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ home: game.homeTeam.abbreviation }),
      });

      const data = await response.json();

      if (!data.home_win_probs) return;

      const rawhomeWP = data.home_win_probs[game.homeTeam.abbreviation] ?? 0;
      const homeWP = parseFloat((100*rawhomeWP).toFixed(2))
      const rawvisitorWP = 100 - homeWP;
      const visitorWP = parseFloat(rawvisitorWP.toFixed(2))
      
      setLiveGames((prev) =>
        prev.map((g) =>
          g.id === game.id
            ? {
                ...g,
                homeTeam: { ...g.homeTeam, winProb: homeWP },
                visitorTeam: { ...g.visitorTeam, winProb: visitorWP }
              }
            : g
        )
      );

    } catch (error) {
      console.error("Error running calculations:", error);
    }

  };



  useEffect(() => {
    // Fetch immediately on mount
    fetchLiveScores();

    const intervalId = setInterval(fetchLiveScores, 10000); 

    // Cleanup function to clear the interval when the component is unmounted
    return () => clearInterval(intervalId);
  }, []); // Empty dependency array means this runs once on mount

  // --- Conditional Rendering for Loading and Errors ---
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-xl text-gray-700">
        Loading NBA scores...
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center text-xl text-red-600">
        Error: {error}
        <p className='text-sm text-gray-500 mt-2'>Check your Python server console for details.</p>
      </div>
    );
  }

  // --- Final Render ---
  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4 flex flex-col items-center">
      <h1 className="text-3xl font-black text-gray-900 mb-8 tracking-tight">
        NBA <span className="text-blue-600">Live</span> Scores
      </h1>
      
      <div className="w-full flex flex-col items-center space-y-4 pb-10">
        {/* Render the fetched liveGames */}
        {liveGames.length > 0 ? (
          liveGames.map((game) => (
            <GameCard 
              key={game.id} 
              game={game} 
              onCalculate={runCalculationsForGame}   // <-- ADD THIS
            />
          ))
        ) : (
          <p className="text-gray-500">No NBA games are currently live or scheduled today.</p>
        )}
      </div>
    </div>
  );
};

export default App;