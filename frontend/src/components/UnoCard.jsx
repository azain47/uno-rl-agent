import React from 'react';
import { cn } from '../lib/utils';

// Function to parse card string (e.g., "r-5", "g-skip", "wild")
function parseCard(cardString) {
    if (!cardString || typeof cardString !== 'string') {
        return { color: 'unknown', value: '?', display: '?' };
    }
    const parts = cardString.split('-');
    let color = parts[0];
    let value = parts.length > 1 ? parts.slice(1).join('-') : color;
    let display = value.replace(/_/g, ' ');

    // Standardize display for special cards
    if (value === 'skip') display = 'Skip';
    else if (value === 'reverse') display = 'Reverse';
    else if (value === 'draw_2') display = 'Draw 2';
    else if (value === 'wild') { display = 'Wild'; color = 'wild'; }
    else if (value === 'wild_draw_4') { display = 'Wild D4'; color = 'wild_draw_4'; }
    else if (value === 'draw_card') { display = 'Draw'; color = 'draw'; }
    else display = display.toUpperCase(); // Number cards

    return { color, value, display };
}

function UnoCard({ cardString, isPlayable, onClick, small = false, className = "", style = {}, disabled = false }) {
    const { color, display } = parseCard(cardString);

    // Map UNO colors to Tailwind CSS classes
    const colorClasses = {
        'r': 'bg-uno-red text-white',
        'g': 'bg-uno-green text-white',
        'b': 'bg-uno-blue text-white',
        'y': 'bg-uno-yellow text-black',
        'wild': 'bg-gradient-to-br from-uno-red from-10% via-uno-yellow via-30% via-uno-green via-60% to-uno-blue text-white border border-black',
        'wild_draw_4': 'bg-gradient-to-br from-uno-red from-10% via-uno-yellow via-30% via-uno-green via-60% to-uno-blue text-white border border-black',
        'draw': 'bg-gray-700 text-white',
        'unknown': 'bg-gray-800 text-white'
    };

    const handleClick = () => {
        if (isPlayable && !disabled && onClick) {
            onClick();
        }
    };

    return (
        <div 
            className={cn(
                "relative flex items-center justify-center text-center font-bold rounded-lg shadow-md transition-all",
                small ? "w-12 h-16 text-xs" : "w-20 h-28 text-lg",
                colorClasses[color] || 'bg-gray-800 text-white',
                isPlayable && !disabled ? 
                  "cursor-pointer border-2 border-white shadow-yellow-300/50 hover:scale-105 hover:-translate-y-1" : 
                  "cursor-default",
                disabled ? "opacity-60 pointer-events-none" : "",
                color !== 'wild' && color !== 'wild_draw_4' && color !== 'draw' && "before:content-[''] before:absolute before:w-3/4 before:h-3/4 before:rounded-full before:bg-white before:opacity-30",
                className
            )}
            onClick={handleClick}
            style={style}
        >
            <span className="relative z-10 drop-shadow-md">{display}</span>
        </div>
    );
}

export default UnoCard; 