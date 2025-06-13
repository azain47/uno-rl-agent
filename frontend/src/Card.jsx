import React from 'react';

// Function to parse card string (e.g., "r-5", "g-skip", "wild")
function parseCard(cardString) {
    if (!cardString || typeof cardString !== 'string') {
        return { color: 'unknown', value: '?', display: '?' };
    }
    const parts = cardString.split('-');
    let color = parts[0];
    let value = parts.length > 1 ? parts.slice(1).join('-') : color; // Handles multi-part values like "draw_4"
    let display = value.replace(/_/g, ' '); // Replace underscores for display

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

function Card({ cardString, isPlayable, onClick, small = false }) {
    const { color, display } = parseCard(cardString);

    const cardClasses = [
        'card',
        color, // Class for color styling (e.g., 'r', 'g', 'b', 'y', 'wild')
        isPlayable ? 'playable' : '',
        small ? 'card-small' : ''
    ].filter(Boolean).join(' ');

    const handleClick = () => {
        if (isPlayable && onClick) {
            onClick();
        }
    };

    return (
        <div className={cardClasses} onClick={handleClick}>
            {display}
        </div>
    );
}

export default Card; 