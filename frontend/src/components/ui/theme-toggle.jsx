import React, { useState, useEffect } from 'react';
import { Button } from './button';

export function ThemeToggle() {
  const [darkMode, setDarkMode] = useState(false);
  
  useEffect(() => {
    // Check for dark mode preference
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    setDarkMode(isDarkMode);
    
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, []);
  
  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    
    localStorage.setItem('darkMode', newDarkMode.toString());
  };
  
  return (
    <Button 
      onClick={toggleDarkMode} 
      variant="outline" 
      size="sm" 
      className="fixed top-4 right-4 z-50"
    >
      {darkMode ? '🌞' : '🌙'}
    </Button>
  );
} 