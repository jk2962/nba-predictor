/**
 * Date utilities for consistent date display.
 * Prevents timezone shifting issues.
 */

/**
 * Format a date string for display.
 * Input: "2026-02-04" (from API)
 * Output: "Feb 4, 2026" or "2/4/2026"
 * 
 * IMPORTANT: Does NOT convert timezones because input is date-only.
 */
export const formatGameDate = (dateString: string | null | undefined, format: 'short' | 'medium' | 'long' = 'short'): string => {
    if (!dateString) return 'N/A';

    // Parse the date string as-is (YYYY-MM-DD)
    // Important: Don't use new Date(dateString) as it may apply timezone
    const [year, month, day] = dateString.split('-').map(Number);

    // Create date in local timezone (no UTC conversion)
    const date = new Date(year, month - 1, day);

    if (format === 'short') {
        // "2/4/2026"
        return `${month}/${day}/${year}`;
    } else if (format === 'medium') {
        // "Feb 4, 2026"
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    } else if (format === 'long') {
        // "February 4, 2026"
        return date.toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric'
        });
    }

    return dateString;
};

/**
 * Format date for display relative to today.
 * Examples: "Today", "Yesterday", "2 days ago", "Feb 4"
 */
export const formatRelativeDate = (dateString: string | null | undefined): string => {
    if (!dateString) return 'N/A';

    const [year, month, day] = dateString.split('-').map(Number);
    const gameDate = new Date(year, month - 1, day);
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Reset time to midnight

    const diffTime = today.getTime() - gameDate.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays === -1) return 'Tomorrow';
    if (diffDays > 1 && diffDays <= 7) return `${diffDays} days ago`;
    if (diffDays < -1 && diffDays >= -7) return `In ${Math.abs(diffDays)} days`;

    // For older/future dates, show month and day
    return gameDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
    });
};

/**
 * Get days since a game was played.
 */
export const getDaysSince = (dateString: string | null | undefined): number | null => {
    if (!dateString) return null;

    const [year, month, day] = dateString.split('-').map(Number);
    const gameDate = new Date(year, month - 1, day);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const diffTime = today.getTime() - gameDate.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    return diffDays;
};

/**
 * Sort dates correctly (newest first).
 */
export const sortByDateDesc = <T extends { game_date: string }>(a: T, b: T): number => {
    return b.game_date.localeCompare(a.game_date);
};

/**
 * Sort dates correctly (oldest first).
 */
export const sortByDateAsc = <T extends { game_date: string }>(a: T, b: T): number => {
    return a.game_date.localeCompare(b.game_date);
};
