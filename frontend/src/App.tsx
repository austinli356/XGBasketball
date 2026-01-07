// src/App.tsx
import { AnimatePresence, motion } from "framer-motion";
import React, { useState, useEffect, useMemo } from 'react';
import type { Game } from './types'; 

const normalizeLocalDate = (d: Date) =>
  new Date(d.getFullYear(), d.getMonth(), d.getDate());

const DateScroller: React.FC<{ setDate: (d: Date) => void }> = ({ setDate }) => {
  const [centerDate, setCenterDate] = useState(normalizeLocalDate(new Date()));
  const visibleDates = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(centerDate);
      d.setDate(centerDate.getDate() - (3 - i));
      return d;
    });
  }, [centerDate]);
  
  const shift = (amount: number) => {
    const next = normalizeLocalDate(centerDate);
    next.setDate(centerDate.getDate() + amount);

    setCenterDate(next);
    setDate(next)
  };

  return (
    <div className="flex items-center gap-4 p-4">
      <button onClick={() => shift(-1)} className="p-1 text-gray-400 hover:text-black text-xl">&larr;</button>
      
      <div className="flex items-center gap-6">
        {visibleDates.map((date) => {
          const isSelected = date.toDateString() === centerDate.toDateString();
          return (
            <div 
              key={date.toISOString()}
              onClick={() => {setCenterDate(date); setDate(date)}}
              className={`cursor-pointer transition-all duration-200 flex flex-col items-center ${
                isSelected ? 'opacity-100 scale-110' : 'opacity-30 hover:opacity-50'
              }`}
            >
              <span className="text-[10px] font-bold uppercase text-gray-400">{date.toLocaleDateString('en-US', { weekday: 'short' })}</span>
              <span className="text-sm font-black">{date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
              {isSelected && <div className="w-1 h-1 bg-blue-600 rounded-full mt-1" />}
            </div>
          );
        })}
      </div>

      <button onClick={() => shift(1)} className="p-1 text-gray-400 hover:text-black text-xl">&rarr;</button>
    </div>
  );
};


const GameCard: React.FC<{ game: Game, onCalculate: (game: Game) => void }> = ({ game, onCalculate }) => {
    const areWinProbsCalculated = 
      game.homeTeam.winProb !== null && 
      game.visitorTeam.winProb !== null;
    const showButton = !areWinProbsCalculated
    const [lastPlay, setLastPlay] = useState(game.lastPlay);

    useEffect(() => {
      setLastPlay(game.lastPlay);
    }, [game.lastPlay]);

  return (
    <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-4">
      {/* Header: Quarter & Time */}
      <div className="bg-gray-50 px-4 py-2 flex justify-between items-center border-b border-gray-100">
        <span className={`text-xs font-bold uppercase tracking-wider ${game.gameState==2 ? 'text-red-600 animate-pulse' : 'text-gray-500'}`}>
          {game.gameState==2 ? '● Live' : (game.gameState==1 ? 'Upcoming' : 'Final')}
        </span>
        <span className="text-sm font-medium text-gray-700">
          {game.gameStatusText}
          {game.gameState==2 && game.gameStatusText.includes(":") && (<span className="flex left-0 right-0 -bottom-0.5 h-[2px] bg-red-400 origin-left"
                style={{ animation: "underlinePulse 2.5s ease-in-out infinite alternate" }}>
          </span>)}
        </span>
      </div>

      {/* Content: Teams & Scores */}
      <div className="p-5 flex justify-between items-center relative">
        {/* Visitor Team */}
        <div className="flex flex-col items-center w-1/3">
          <img 
            src={`/assets/${game.visitorTeam.abbreviation}.png`} 
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
            src={`/assets/${game.homeTeam.abbreviation}.png`} 
            alt={game.homeTeam.name} 
            className="w-25 h-25 object-contain"
          />
          <p className="text-2xl font-black text-gray-900 mt-1">{game.gameState>1 ? game.homeTeam.score : ""}</p>
        </div>
      </div>
      <div className="mb-1 relative h-8 overflow-hidden px-4 py-2 text-center border-t border-gray-50 text-xs text-gray-600">
        <AnimatePresence mode="popLayout">
          <motion.div
            key={lastPlay}
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -20, opacity: 0, rotate: -6 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="absolute inset-0 flex items-center justify-center"
          >
            {lastPlay}
          </motion.div>
        </AnimatePresence>
      </div>
      {game.homeTeam.winProb !== null && game.visitorTeam.winProb !== null && (
          <div className="relative bottom-0 left-0 w-full h-6 flex justify-center rounded-b">           
            <h3 className="flex flex-col justify-center items-center text-red-600 text-sm">
                <span className="text-center">XGB pregame predicted winner:</span>
                <span className="text-center">
                    {game.visitorTeam.winProb > game.homeTeam.winProb
                        ? game.visitorTeam.name
                        : game.homeTeam.name}{' '}
                    ({game.visitorTeam.winProb > game.homeTeam.winProb
                        ? game.visitorTeam.winProb
                        : game.homeTeam.winProb}%)
                </span>
            </h3>
          </div>
      )}
      {showButton && <button
        onClick={() => onCalculate(game)}
        className="w-full bg-blue-400 text-white py-2 text-sm font-semibold hover:bg-blue-500"
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
  const [date, setDate] = useState(normalizeLocalDate(new Date()));
  const [liveGames, setLiveGames] = useState<Game[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const formatDate = (d: Date) =>
    d.toLocaleDateString("en-CA");

  const fetchLiveScores = async (selectedDate: Date, signal?: AbortSignal) => {
    try {
      const dateStr = formatDate(selectedDate);

      const response = await fetch(
      `/api/nba-scores?date=${encodeURIComponent(dateStr)}`,
      { signal } 
      );

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

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
  } catch (err: any) {
    if (err.name === 'AbortError') {
      console.log('Fetch aborted: newer request is in progress');
      return;
    }
    setError("Could not fetch live scores. Is the Python server running?");
    console.error(err);
  } finally {
    setIsLoading(false); 
  }
};

  const runCalculationsForGame = async (game: Game) => {
    try {
      const response = await fetch("/run-calculations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gameId: game.id }),
      });

      const data = await response.json();

      if (!data.home_win_prob) return;

      const rawhomeWP = data.home_win_prob ?? 0;
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
    const controller = new AbortController();
    let intervalId: number | undefined = undefined;

    fetchLiveScores(date, controller.signal);

    const today = new Date().toLocaleDateString();
    if (today === date.toLocaleDateString()) {
      intervalId = setInterval(() => {
        fetchLiveScores(date, controller.signal);
      }, 15000);
    }

    return () => {
      controller.abort();
      if (intervalId) clearInterval(intervalId);
    };
  }, [date]);

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
        NBA <span className="text-blue-600">XGBoost</span> Model
      </h1>
      <DateScroller
      setDate={setDate}/>
      <div className="w-full flex flex-col items-center space-y-4 pb-10">
        {/* Render the fetched liveGames */}
        {liveGames.length > 0 ? (
          liveGames.map((game) => (
            <GameCard 
              key={game.id} 
              game={game} 
              onCalculate={runCalculationsForGame}   
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