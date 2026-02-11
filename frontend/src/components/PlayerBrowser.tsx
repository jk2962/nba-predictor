/**
 * Player Browser Component - Advanced filtering, sorting, and display
 */
import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { playerApi } from '../services/api';
import type { Player } from '../types';
import PlayerCard from './PlayerCard';

// Filter state type
interface FilterState {
    search: string;
    positions: string[];
    teams: string[];

    sortBy: 'fantasy' | 'ppg' | 'rpg' | 'apg' | 'mpg' | 'name';
    sortOrder: 'asc' | 'desc';
}

const POSITIONS = ['Guard', 'Forward', 'Center'];

const defaultFilters: FilterState = {
    search: '',
    positions: [],
    teams: [],

    sortBy: 'fantasy',
    sortOrder: 'desc',
};

export default function PlayerBrowser() {
    const [searchParams, setSearchParams] = useSearchParams();

    // State
    const [players, setPlayers] = useState<Player[]>([]);
    const [teams, setTeams] = useState<{ name: string; abbreviation: string }[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [total, setTotal] = useState(0);
    const [perPage] = useState(24);
    const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

    // Initialize filters from URL
    const [filters, setFilters] = useState<FilterState>(() => {
        const search = searchParams.get('search') || '';
        const positions = searchParams.get('position')?.split(',').filter(Boolean) || [];
        const teamsParam = searchParams.get('team')?.split(',').filter(Boolean) || [];
        const sortBy = (searchParams.get('sort_by') as FilterState['sortBy']) || 'fantasy';
        const sortOrder = (searchParams.get('sort_order') as FilterState['sortOrder']) || 'desc';

        return {
            ...defaultFilters,
            search,
            positions,
            teams: teamsParam,
            sortBy,
            sortOrder,
        };
    });

    // Debounce search
    const [debouncedSearch, setDebouncedSearch] = useState(filters.search);

    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(filters.search);
        }, 300);
        return () => clearTimeout(timer);
    }, [filters.search]);

    // Fetch teams on mount
    useEffect(() => {
        playerApi.getTeams().then(setTeams).catch(console.error);
    }, []);

    // Sync filters to URL
    useEffect(() => {
        const params = new URLSearchParams();
        if (debouncedSearch) params.set('search', debouncedSearch);
        if (filters.positions.length) params.set('position', filters.positions.join(','));
        if (filters.teams.length) params.set('team', filters.teams.join(','));
        if (filters.sortBy !== 'fantasy') params.set('sort_by', filters.sortBy);
        if (page > 1) params.set('page', String(page));
        setSearchParams(params, { replace: true });
    }, [filters, debouncedSearch, page, setSearchParams]);

    // Fetch players
    const fetchPlayers = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await playerApi.getPlayers({
                page,
                per_page: perPage,
                search: debouncedSearch || undefined,
                position: filters.positions.length ? filters.positions.join(',') : undefined,
                team: filters.teams.length ? filters.teams.join(',') : undefined,
                sort_by: filters.sortBy,
                sort_order: filters.sortOrder,
            });

            setPlayers(response.items);
            setTotalPages(response.pages);
            setTotal(response.total);
        } catch (err) {
            setError('Failed to load players');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [page, perPage, debouncedSearch, filters]);

    useEffect(() => {
        fetchPlayers();
    }, [fetchPlayers]);

    // Reset page when filters change
    useEffect(() => {
        setPage(1);
    }, [debouncedSearch, filters.positions, filters.teams]);

    // Filter handlers
    const updateFilter = useCallback(<K extends keyof FilterState>(key: K, value: FilterState[K]) => {
        setFilters(prev => ({ ...prev, [key]: value }));
    }, []);

    const togglePosition = (pos: string) => {
        setFilters(prev => ({
            ...prev,
            positions: prev.positions.includes(pos)
                ? prev.positions.filter(p => p !== pos)
                : [...prev.positions, pos],
        }));
    };

    // Team selection is handled by the multi-select dropdown

    const clearFilters = () => {
        setFilters(defaultFilters);
        setPage(1);
    };



    // Render active filter chips
    const renderActiveFilters = () => {
        const chips: { label: string; onRemove: () => void }[] = [];

        if (filters.positions.length) {
            chips.push({
                label: `Position: ${filters.positions.join(', ')}`,
                onRemove: () => updateFilter('positions', []),
            });
        }

        if (filters.teams.length) {
            chips.push({
                label: `Team: ${filters.teams.join(', ')}`,
                onRemove: () => updateFilter('teams', []),
            });
        }

        if (!chips.length) return null;

        return (
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                {chips.map(chip => (
                    <div
                        key={chip.label}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.25rem 0.75rem',
                            background: 'var(--surface-2)',
                            borderRadius: 'var(--radius-full)',
                            fontSize: '0.875rem',
                        }}
                    >
                        <span>{chip.label}</span>
                        <button
                            onClick={chip.onRemove}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: 'var(--text-secondary)',
                                cursor: 'pointer',
                                padding: 0,
                                fontSize: '1rem',
                                lineHeight: 1,
                            }}
                        >
                            ×
                        </button>
                    </div>
                ))}
                <button
                    onClick={clearFilters}
                    style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--hot)',
                        cursor: 'pointer',
                        fontSize: '0.875rem',
                    }}
                >
                    Clear All
                </button>
            </div>
        );
    };

    return (
        <div className="player-browser" style={{
            display: 'grid',
            gridTemplateColumns: '260px 1fr',
            gap: '2rem',
            alignItems: 'start',
            maxWidth: '1600px',
            margin: '0 auto',
            paddingBottom: '2rem'
        }}>
            {/* Sidebar Filters */}
            <div style={{
                position: 'sticky',
                top: '2rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.5rem',
                maxHeight: 'calc(100vh - 4rem)',
                overflowY: 'auto',
                paddingRight: '0.5rem'
            }}>
                <div>
                    <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Filters</h2>

                    {/* Search */}
                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                            Search
                        </label>
                        <input
                            type="text"
                            placeholder="Player or Team..."
                            value={filters.search}
                            onChange={(e) => updateFilter('search', e.target.value)}
                            className="input"
                            style={{ width: '100%' }}
                        />
                    </div>

                    {/* Position Filter */}
                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                            Position
                        </label>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            {POSITIONS.map(pos => (
                                <button
                                    key={pos}
                                    onClick={() => togglePosition(pos)}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        padding: '0.5rem 0.75rem',
                                        background: filters.positions.includes(pos) ? 'var(--hot)' : 'var(--surface-2)',
                                        border: '1px solid var(--border)',
                                        borderRadius: 'var(--radius-md)',
                                        color: filters.positions.includes(pos) ? 'white' : 'var(--text-primary)',
                                        cursor: 'pointer',
                                        fontSize: '0.875rem',
                                        textAlign: 'left',
                                        transition: 'all 0.15s ease'
                                    }}
                                >
                                    <span>{pos}</span>
                                    {filters.positions.includes(pos) && <span>✓</span>}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Team Filter */}
                    <div>
                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                            Teams
                        </label>
                        <select
                            multiple
                            value={filters.teams}
                            onChange={(e) => {
                                const selected = Array.from(e.target.selectedOptions, opt => opt.value);
                                updateFilter('teams', selected);
                            }}
                            style={{
                                width: '100%',
                                height: '200px',
                                padding: '0.5rem',
                                background: 'var(--surface-2)',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--radius-md)',
                                color: 'var(--text-primary)',
                                fontSize: '0.875rem'
                            }}
                        >
                            {teams.map(team => (
                                <option key={team.abbreviation} value={team.abbreviation} style={{ padding: '0.25rem' }}>
                                    {team.abbreviation} - {team.name}
                                </option>
                            ))}
                        </select>
                        <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: '0.5rem' }}>
                            Hold Cmd/Ctrl to select multiple
                        </p>
                    </div>
                </div>

                {/* Reset Filters */}
                <button
                    onClick={clearFilters}
                    className="btn btn-secondary"
                    style={{ width: '100%' }}
                >
                    Reset All Filters
                </button>
            </div>

            {/* Main Content */}
            <div style={{ minWidth: 0 }}>
                {/* Header & Controls */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'end',
                    marginBottom: '1.5rem',
                    flexWrap: 'wrap',
                    gap: '1rem'
                }}>
                    <div>
                        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Browse Players</h1>
                        <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                            {loading ? 'Loading...' : `Showing ${total} players`}
                        </p>
                    </div>

                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        {/* Sort Dropdown */}
                        <select
                            value={`${filters.sortBy}-${filters.sortOrder}`}
                            onChange={(e) => {
                                const [sortBy, sortOrder] = e.target.value.split('-') as [FilterState['sortBy'], FilterState['sortOrder']];
                                setFilters(prev => ({ ...prev, sortBy, sortOrder }));
                            }}
                            className="input"
                            style={{ width: 'auto', minWidth: '160px' }}
                        >
                            <option value="fantasy-desc">Fantasy Score ↓</option>
                            <option value="fantasy-asc">Fantasy Score ↑</option>
                            <option value="ppg-desc">Points (PPG) ↓</option>
                            <option value="ppg-asc">Points (PPG) ↑</option>
                            <option value="rpg-desc">Rebounds (RPG) ↓</option>
                            <option value="rpg-asc">Rebounds (RPG) ↑</option>
                            <option value="apg-desc">Assists (APG) ↓</option>
                            <option value="apg-asc">Assists (APG) ↑</option>
                            <option value="mpg-desc">Minutes (MPG) ↓</option>
                            <option value="mpg-asc">Minutes (MPG) ↑</option>
                            <option value="name-asc">Name (A-Z)</option>
                            <option value="name-desc">Name (Z-A)</option>
                        </select>

                        {/* View Toggle */}
                        <div style={{
                            display: 'flex',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--radius-md)',
                            overflow: 'hidden',
                        }}>
                            <button
                                onClick={() => setViewMode('grid')}
                                style={{
                                    padding: '0.5rem 0.75rem',
                                    background: viewMode === 'grid' ? 'var(--hot)' : 'var(--surface-2)',
                                    border: 'none',
                                    color: viewMode === 'grid' ? 'white' : 'var(--text-primary)',
                                    cursor: 'pointer',
                                }}
                                title="Grid View"
                            >
                                ▦
                            </button>
                            <button
                                onClick={() => setViewMode('table')}
                                style={{
                                    padding: '0.5rem 0.75rem',
                                    background: viewMode === 'table' ? 'var(--hot)' : 'var(--surface-2)',
                                    border: 'none',
                                    color: viewMode === 'table' ? 'white' : 'var(--text-primary)',
                                    cursor: 'pointer',
                                }}
                                title="Table View"
                            >
                                ☰
                            </button>
                        </div>
                    </div>
                </div>

                {/* Active Filters (Chips) */}
                {renderActiveFilters()}

                {/* Error State */}
                {error && (
                    <div style={{
                        padding: '3rem',
                        textAlign: 'center',
                        background: 'var(--surface-1)',
                        borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--error)',
                        marginBottom: '2rem'
                    }}>
                        <p style={{ color: 'var(--error)', marginBottom: '1rem', fontSize: '1.1rem' }}>{error}</p>
                        <button onClick={fetchPlayers} className="btn btn-primary">Try Again</button>
                    </div>
                )}

                {/* Loading State */}
                {loading && (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(3, 1fr)',
                        gap: '1.5rem',
                    }}>
                        {Array.from({ length: 12 }).map((_, i) => (
                            <div
                                key={i}
                                style={{
                                    height: '280px',
                                    background: 'var(--surface-1)',
                                    borderRadius: 'var(--radius-lg)',
                                    animation: 'pulse 1.5s infinite',
                                }}
                            />
                        ))}
                    </div>
                )}

                {/* Grid View */}
                {!loading && !error && viewMode === 'grid' && (
                    <div key={page} className="page-transition" style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(3, 1fr)',
                        gap: '1.5rem',
                    }}>
                        {players.map(player => (
                            <PlayerCard
                                key={player.id}
                                player={player}
                                statFilter={
                                    filters.sortBy === 'ppg' ? 'points' :
                                        filters.sortBy === 'rpg' ? 'rebounds' :
                                            filters.sortBy === 'apg' ? 'assists' :
                                                'fantasy'
                                }
                            />
                        ))}
                    </div>
                )}

                {/* Table View */}
                {!loading && !error && viewMode === 'table' && (
                    <div key={page} className="page-transition" style={{
                        overflow: 'auto',
                        background: 'var(--surface-1)',
                        borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--border)'
                    }}>
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Player</th>
                                    <th>Team</th>
                                    <th style={{ textAlign: 'center' }}>Pos</th>
                                    <th style={{ textAlign: 'right' }}>PPG</th>
                                    <th style={{ textAlign: 'right' }}>RPG</th>
                                    <th style={{ textAlign: 'right' }}>APG</th>
                                    <th style={{ textAlign: 'right' }}>MPG</th>
                                    <th style={{ textAlign: 'right' }}>Fantasy</th>
                                </tr>
                            </thead>
                            <tbody>
                                {players.map((player, idx) => (
                                    <tr
                                        key={player.id}
                                        style={{
                                            background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                                            cursor: 'pointer'
                                        }}
                                        onClick={() => window.location.href = `/player/${player.id}`}
                                    >
                                        <td>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                <img
                                                    src={player.headshot_url || `https://cdn.nba.com/headshots/nba/latest/260x190/${player.nba_id}.png`}
                                                    alt=""
                                                    style={{
                                                        width: '32px',
                                                        height: '32px',
                                                        borderRadius: 'var(--radius-full)',
                                                        objectFit: 'cover',
                                                        backgroundColor: 'var(--surface-3)',
                                                    }}
                                                    onError={(e) => {
                                                        (e.target as HTMLImageElement).style.display = 'none';
                                                    }}
                                                />
                                                <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{player.name}</span>
                                            </div>
                                        </td>
                                        <td>{player.team_abbreviation}</td>
                                        <td style={{ textAlign: 'center' }}>
                                            <span className={`position-badge position-${player.position?.charAt(0)}`}>
                                                {player.position?.charAt(0)}
                                            </span>
                                        </td>
                                        <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{player.season_ppg?.toFixed(1) || '-'}</td>
                                        <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{player.season_rpg?.toFixed(1) || '-'}</td>
                                        <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{player.season_apg?.toFixed(1) || '-'}</td>
                                        <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{player.season_mpg?.toFixed(1) || '-'}</td>
                                        <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 600, color: 'var(--hot)' }}>{player.fantasy_score?.toFixed(1) || '-'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Empty State */}
                {!loading && !error && players.length === 0 && (
                    <div style={{
                        padding: '4rem 2rem',
                        textAlign: 'center',
                        background: 'var(--surface-1)',
                        borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--border)'
                    }}>
                        <h3 style={{ margin: '0 0 0.5rem', color: 'var(--text-primary)' }}>No players found</h3>
                        <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                            Try adjusting your filters or search criteria
                        </p>
                        <button
                            onClick={clearFilters}
                            className="btn btn-primary"
                            style={{ marginTop: '1.5rem' }}
                        >
                            Clear All Filters
                        </button>
                    </div>
                )}

                {/* Pagination */}
                {!loading && !error && totalPages > 1 && (
                    <div style={{
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        gap: '1rem',
                        marginTop: '2rem'
                    }}>
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="btn btn-secondary"
                        >
                            Previous
                        </button>

                        <span style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                            Page <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{page}</span> of {totalPages}
                        </span>

                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages}
                            className="btn btn-secondary"
                        >
                            Next
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
