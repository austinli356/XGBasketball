// src/App.tsx
import React, { useState, useEffect } from 'react';
import type { Game} from './types'; 


const getLogoUrl = (text: string, color: string) => 
  `https://placehold.co/80x80/${color.replace('#', '')}/FFFFFF?text=${text}`;

const GameCard: React.FC<{ game: Game }> = ({ game }) => {
  return (
    <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-4">
      {/* Header: Quarter & Time */}
      <div className="bg-gray-50 px-4 py-2 flex justify-between items-center border-b border-gray-100">
        <span className={`text-xs font-bold uppercase tracking-wider ${game.isLive ? 'text-red-600 animate-pulse' : 'text-gray-500'}`}>
          {game.isLive ? '● Live' : 'Final'}
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
            src={getLogoUrl(game.visitorTeam.abbreviation, game.visitorTeam.color)} 
            alt={game.visitorTeam.name} 
            className="w-16 h-16 rounded-full mb-2 object-cover"
          />
          <h3 className="font-bold text-gray-800 text-lg">{game.visitorTeam.abbreviation}</h3>
          <p className="text-3xl font-black text-gray-900 mt-1">{game.visitorTeam.score}</p>
        </div>

        {/* VS / Divider */}
        <div className="flex flex-col items-center w-1/3 px-2">
          <span className="text-gray-300 font-bold text-xl italic">VS</span>
        </div>

        {/* Home Team */}
        <div className="flex flex-col items-center w-1/3">
          <img 
            src={getLogoUrl(game.homeTeam.abbreviation, game.homeTeam.color)} 
            alt={game.homeTeam.name} 
            className="w-16 h-16 rounded-full mb-2 object-cover"
          />
          <h3 className="font-bold text-gray-800 text-lg">{game.homeTeam.abbreviation}</h3>
          <p className="text-3xl font-black text-gray-900 mt-1">{game.homeTeam.score}</p>
        </div>

        {/* Win Probability Bar */}
        {game.homeTeam.winProb !== undefined && game.visitorTeam.winProb !== undefined && (
          <div className="absolute bottom-0 left-0 w-full h-2 flex rounded-b">
            <div
              className="bg-blue-500 h-full rounded-l"
              style={{ width: `${game.visitorTeam.winProb * 100}%` }}
            ></div>
            <div
              className="bg-red-500 h-full rounded-r"
              style={{ width: `${game.homeTeam.winProb * 100}%` }}
            ></div>
          </div>
        )}
      </div>
      
      {/* Footer: Detailed Team Name */}
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
      setLiveGames(data);
      setError(null);
    } catch (err) {
      setError("Could not fetch live scores. Is the Python server running?");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Fetch immediately on mount
    fetchLiveScores();

    // Set up an interval to refresh the scores every 30 seconds
    const intervalId = setInterval(fetchLiveScores, 3000000); 

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
            <GameCard key={game.id} game={game} />
          ))
        ) : (
          <p className="text-gray-500">No NBA games are currently live or scheduled today.</p>
        )}
      </div>
    </div>
  );
};

export default App;