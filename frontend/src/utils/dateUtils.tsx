/**
 * Format a timestamp into a relative time string (e.g., "2m ago", "5h ago")
 */
export const formatRelativeTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    // Handle future dates or invalid dates
    if (seconds < 0 || isNaN(seconds)) {
      return 'just now';
    }
    
    // Time intervals in seconds
    const intervals = {
      year: 31536000,
      month: 2592000,
      week: 604800,
      day: 86400,
      hour: 3600,
      minute: 60
    };
    
    let counter;
    
    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
      counter = Math.floor(seconds / secondsInUnit);
      if (counter > 0) {
        return `${counter} ${unit}${counter === 1 ? '' : 's'} ago`;
      }
    }
    
    return 'just now';
  };