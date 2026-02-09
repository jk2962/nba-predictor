/**
 * Browse Page - Advanced Player Browser with filtering and sorting
 */
import PlayerBrowser from '../components/PlayerBrowser';

export default function BrowsePage() {
    return (
        <div className="container" style={{ padding: 'var(--space-2xl) var(--space-lg)' }}>
            <PlayerBrowser />
        </div>
    );
}
