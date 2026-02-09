/**
 * Player Browser Component - Advanced filtering, sorting, and display
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { playerApi } from '../services/api';
import type { Player } from '../types';
import PlayerCard from './PlayerCard';

// Filter state type
interface FilterState {
    search: string;
    positions: string[];
    teams: string[];
    ppg: { min: number | null; max: number | null };
    rpg: { min: number | null; max: number | null };
    apg: { min: number | null; max: number | null };
    mpg: { min: number | null; max: number | null };
    sortBy: 'fantasy' | 'ppg' | 'rpg' | 'apg' | 'mpg' | 'name';
    sortOrder: 'asc' | 'desc';
}

const POSITIONS = ['PG', 'SG', 'SF', 'PF', 'C'];

const defaultFilters: FilterState = {
    search: '',
    positions: [],
    teams: [],
    ppg: { min: null, max: null },
    rpg: { min: null, max: null },
    apg: { min: null, max: null },
    mpg: { min: null, max: null },
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
    const [filtersExpanded, setFiltersExpanded] = useState(true);

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
        if (filters.sortOrder !== 'desc') params.set('sort_order', filters.sortOrder);
        if (filters.ppg.min) params.set('ppg_min', String(filters.ppg.min));
        if (filters.ppg.max) params.set('ppg_max', String(filters.ppg.max));
        if (filters.rpg.min) params.set('rpg_min', String(filters.rpg.min));
        if (filters.rpg.max) params.set('rpg_max', String(filters.rpg.max));
        if (filters.apg.min) params.set('apg_min', String(filters.apg.min));
        if (filters.apg.max) params.set('apg_max', String(filters.apg.max));
        if (filters.mpg.min) params.set('mpg_min', String(filters.mpg.min));
        if (filters.mpg.max) params.set('mpg_max', String(filters.mpg.max));
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
                ppg_min: filters.ppg.min ?? undefined,
                ppg_max: filters.ppg.max ?? undefined,
                rpg_min: filters.rpg.min ?? undefined,
                rpg_max: filters.rpg.max ?? undefined,
                apg_min: filters.apg.min ?? undefined,
                apg_max: filters.apg.max ?? undefined,
                mpg_min: filters.mpg.min ?? undefined,
                mpg_max: filters.mpg.max ?? undefined,
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
    }, [debouncedSearch, filters.positions, filters.teams, filters.ppg, filters.rpg, filters.apg, filters.mpg]);

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

    // Active filter count
    const activeFilterCount = useMemo(() => {
        let count = 0;
        if (filters.positions.length) count++;
        if (filters.teams.length) count++;
        if (filters.ppg.min || filters.ppg.max) count++;
        if (filters.rpg.min || filters.rpg.max) count++;
        if (filters.apg.min || filters.apg.max) count++;
        if (filters.mpg.min || filters.mpg.max) count++;
        return count;
    }, [filters]);

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

        if (filters.ppg.min || filters.ppg.max) {
            chips.push({
                label: `PPG: ${filters.ppg.min || 0}-${filters.ppg.max || '∞'}`,
                onRemove: () => updateFilter('ppg', { min: null, max: null }),
            });
        }

        if (filters.rpg.min || filters.rpg.max) {
            chips.push({
                label: `RPG: ${filters.rpg.min || 0}-${filters.rpg.max || '∞'}`,
                onRemove: () => updateFilter('rpg', { min: null, max: null }),
            });
        }

        if (filters.apg.min || filters.apg.max) {
            chips.push({
                label: `APG: ${filters.apg.min || 0}-${filters.apg.max || '∞'}`,
                onRemove: () => updateFilter('apg', { min: null, max: null }),
            });
        }

        if (filters.mpg.min || filters.mpg.max) {
            chips.push({
                label: `MPG: ${filters.mpg.min || 0}-${filters.mpg.max || '∞'}`,
                onRemove: () => updateFilter('mpg', { min: null, max: null }),
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
        <div className="player-browser">
            {/* Header */}
            <div style={{ marginBottom: '1.5rem' }}>
                <h2 style={{ margin: 0, marginBottom: '0.5rem' }}>Browse All Players</h2>
                <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                    {loading ? 'Loading...' : `Showing ${players.length} of ${total} players`}
                </p>
            </div>

            {/* Search Bar */}
            <div style={{ marginBottom: '1rem' }}>
                <input
                    type="text"
                    placeholder="Search players, teams..."
                    value={filters.search}
                    onChange={(e) => updateFilter('search', e.target.value)}
                    style={{
                        width: '100%',
                        padding: '0.75rem 1rem',
                        fontSize: '1rem',
                        background: 'var(--surface-1)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-md)',
                        color: 'var(--text-primary)',
                    }}
                />
            </div>

            {/* Active Filters */}
            {renderActiveFilters()}

            {/* Controls Row */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '1rem',
                marginBottom: '1rem',
                flexWrap: 'wrap',
            }}>
                {/* Toggle Filters Button */}
                <button
                    onClick={() => setFiltersExpanded(!filtersExpanded)}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.5rem 1rem',
                        background: 'var(--surface-2)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-md)',
                        color: 'var(--text-primary)',
                        cursor: 'pointer',
                    }}
                >
                    <span>Filters</span>
                    {activeFilterCount > 0 && (
                        <span style={{
                            background: 'var(--hot)',
                            color: 'white',
                            padding: '0.125rem 0.5rem',
                            borderRadius: 'var(--radius-full)',
                            fontSize: '0.75rem',
                        }}>
                            {activeFilterCount}
                        </span>
                    )}
                    <span>{filtersExpanded ? '▲' : '▼'}</span>
                </button>

                {/* Right Side Controls */}
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    {/* Sort Dropdown */}
                    <select
                        value={`${filters.sortBy}-${filters.sortOrder}`}
                        onChange={(e) => {
                            const [sortBy, sortOrder] = e.target.value.split('-') as [FilterState['sortBy'], FilterState['sortOrder']];
                            setFilters(prev => ({ ...prev, sortBy, sortOrder }));
                        }}
                        style={{
                            padding: '0.5rem 1rem',
                            background: 'var(--surface-2)',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--radius-md)',
                            color: 'var(--text-primary)',
                            cursor: 'pointer',
                        }}
                    >
                        <option value="fantasy-desc">Fantasy ↓</option>
                        <option value="fantasy-asc">Fantasy ↑</option>
                        <option value="ppg-desc">PPG ↓</option>
                        <option value="ppg-asc">PPG ↑</option>
                        <option value="rpg-desc">RPG ↓</option>
                        <option value="rpg-asc">RPG ↑</option>
                        <option value="apg-desc">APG ↓</option>
                        <option value="apg-asc">APG ↑</option>
                        <option value="mpg-desc">MPG ↓</option>
                        <option value="mpg-asc">MPG ↑</option>
                        <option value="name-asc">Name A-Z</option>
                        <option value="name-desc">Name Z-A</option>
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
                        >
                            ☰
                        </button>
                    </div>
                </div>
            </div>

            {/* Expandable Filters Panel */}
            {filtersExpanded && (
                <div
                    style={{
                        padding: '1rem',
                        background: 'var(--surface-1)',
                        borderRadius: 'var(--radius-lg)',
                        marginBottom: '1.5rem',
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '1.5rem',
                    }}
                >
                    {/* Position Filter */}
                    <div>
                        <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                            Position
                        </h4>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                            {POSITIONS.map(pos => (
                                <button
                                    key={pos}
                                    onClick={() => togglePosition(pos)}
                                    style={{
                                        padding: '0.375rem 0.75rem',
                                        background: filters.positions.includes(pos)
                                            ? 'var(--hot)'
                                            : 'var(--surface-2)',
                                        border: '1px solid var(--border)',
                                        borderRadius: 'var(--radius-sm)',
                                        color: filters.positions.includes(pos) ? 'white' : 'var(--text-primary)',
                                        cursor: 'pointer',
                                        fontSize: '0.875rem',
                                    }}
                                >
                                    {pos}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Team Filter */}
                    <div>
                        <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                            Team
                        </h4>
                        <select
                            multiple
                            value={filters.teams}
                            onChange={(e) => {
                                const selected = Array.from(e.target.selectedOptions, opt => opt.value);
                                updateFilter('teams', selected);
                            }}
                            style={{
                                width: '100%',
                                height: '120px',
                                padding: '0.5rem',
                                background: 'var(--surface-2)',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--radius-md)',
                                color: 'var(--text-primary)',
                            }}
                        >
                            {teams.map(team => (
                                <option key={team.abbreviation} value={team.abbreviation}>
                                    {team.abbreviation} - {team.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Stat Ranges */}
                    <div>
                        <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                            PPG Range
                        </h4>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                            <input
                                type="number"
                                placeholder="Min"
                                value={filters.ppg.min ?? ''}
                                onChange={(e) => updateFilter('ppg', {
                                    ...filters.ppg,
                                    min: e.target.value ? Number(e.target.value) : null,
                                })}
                                style={{
                                    width: '70px',
                                    padding: '0.375rem',
                                    background: 'var(--surface-2)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                            <span>-</span>
                            <input
                                type="number"
                                placeholder="Max"
                                value={filters.ppg.max ?? ''}
                                onChange={(e) => updateFilter('ppg', {
                                    ...filters.ppg,
                                    max: e.target.value ? Number(e.target.value) : null,
                                })}
                                style={{
                                    width: '70px',
                                    padding: '0.375rem',
                                    background: 'var(--surface-2)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                        </div>
                    </div>

                    <div>
                        <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                            RPG Range
                        </h4>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                            <input
                                type="number"
                                placeholder="Min"
                                value={filters.rpg.min ?? ''}
                                onChange={(e) => updateFilter('rpg', {
                                    ...filters.rpg,
                                    min: e.target.value ? Number(e.target.value) : null,
                                })}
                                style={{
                                    width: '70px',
                                    padding: '0.375rem',
                                    background: 'var(--surface-2)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                            <span>-</span>
                            <input
                                type="number"
                                placeholder="Max"
                                value={filters.rpg.max ?? ''}
                                onChange={(e) => updateFilter('rpg', {
                                    ...filters.rpg,
                                    max: e.target.value ? Number(e.target.value) : null,
                                })}
                                style={{
                                    width: '70px',
                                    padding: '0.375rem',
                                    background: 'var(--surface-2)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                        </div>
                    </div>

                    <div>
                        <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                            APG Range
                        </h4>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                            <input
                                type="number"
                                placeholder="Min"
                                value={filters.apg.min ?? ''}
                                onChange={(e) => updateFilter('apg', {
                                    ...filters.apg,
                                    min: e.target.value ? Number(e.target.value) : null,
                                })}
                                style={{
                                    width: '70px',
                                    padding: '0.375rem',
                                    background: 'var(--surface-2)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                            <span>-</span>
                            <input
                                type="number"
                                placeholder="Max"
                                value={filters.apg.max ?? ''}
                                onChange={(e) => updateFilter('apg', {
                                    ...filters.apg,
                                    max: e.target.value ? Number(e.target.value) : null,
                                })}
                                style={{
                                    width: '70px',
                                    padding: '0.375rem',
                                    background: 'var(--surface-2)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                        </div>
                    </div>

                    <div>
                        <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                            MPG Range
                        </h4>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                            <input
                                type="number"
                                placeholder="Min"
                                value={filters.mpg.min ?? ''}
                                onChange={(e) => updateFilter('mpg', {
                                    ...filters.mpg,
                                    min: e.target.value ? Number(e.target.value) : null,
                                })}
                                style={{
                                    width: '70px',
                                    padding: '0.375rem',
                                    background: 'var(--surface-2)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                            <span>-</span>
                            <input
                                type="number"
                                placeholder="Max"
                                value={filters.mpg.max ?? ''}
                                onChange={(e) => updateFilter('mpg', {
                                    ...filters.mpg,
                                    max: e.target.value ? Number(e.target.value) : null,
                                })}
                                style={{
                                    width: '70px',
                                    padding: '0.375rem',
                                    background: 'var(--surface-2)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                        </div>
                    </div>
                </div>
            )}

            {/* Error State */}
            {error && (
                <div style={{
                    padding: '2rem',
                    textAlign: 'center',
                    background: 'var(--surface-1)',
                    borderRadius: 'var(--radius-lg)',
                }}>
                    <p style={{ color: 'var(--text-secondary)' }}>{error}</p>
                    <button
                        onClick={fetchPlayers}
                        style={{
                            padding: '0.5rem 1rem',
                            background: 'var(--hot)',
                            border: 'none',
                            borderRadius: 'var(--radius-md)',
                            color: 'white',
                            cursor: 'pointer',
                        }}
                    >
                        Retry
                    </button>
                </div>
            )}

            {/* Loading State */}
            {loading && (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                    gap: '1.5rem',
                }}>
                    {Array.from({ length: 12 }).map((_, i) => (
                        <div
                            key={i}
                            style={{
                                height: '200px',
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
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                    gap: '1.5rem',
                }}>
                    {players.map(player => (
                        <PlayerCard
                            key={player.id}
                            player={player}
                        />
                    ))}
                </div>
            )}

            {/* Table View */}
            {!loading && !error && viewMode === 'table' && (
                <div style={{
                    overflow: 'auto',
                    background: 'var(--surface-1)',
                    borderRadius: 'var(--radius-lg)',
                }}>
                    <table style={{
                        width: '100%',
                        borderCollapse: 'collapse',
                        fontSize: '0.875rem',
                    }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border)' }}>
                                <th style={{ padding: '1rem', textAlign: 'left' }}>Player</th>
                                <th style={{ padding: '1rem', textAlign: 'left' }}>Team</th>
                                <th style={{ padding: '1rem', textAlign: 'center' }}>Pos</th>
                                <th style={{ padding: '1rem', textAlign: 'right' }}>PPG</th>
                                <th style={{ padding: '1rem', textAlign: 'right' }}>RPG</th>
                                <th style={{ padding: '1rem', textAlign: 'right' }}>APG</th>
                                <th style={{ padding: '1rem', textAlign: 'right' }}>MPG</th>
                                <th style={{ padding: '1rem', textAlign: 'right' }}>Fantasy</th>
                            </tr>
                        </thead>
                        <tbody>
                            {players.map((player, idx) => (
                                <Link
                                    key={player.id}
                                    to={`/player/${player.id}`}
                                    style={{ display: 'contents', textDecoration: 'none', color: 'inherit' }}
                                >
                                    <tr
                                        style={{
                                            borderBottom: '1px solid var(--border)',
                                            background: idx % 2 === 0 ? 'transparent' : 'var(--surface-0)',
                                            cursor: 'pointer',
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.background = 'var(--surface-2)'}
                                        onMouseLeave={(e) => e.currentTarget.style.background = idx % 2 === 0 ? 'transparent' : 'var(--surface-0)'}
                                    >
                                        <td style={{ padding: '0.75rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                            <img
                                                src={player.headshot_url || `https://cdn.nba.com/headshots/nba/latest/260x190/${player.nba_id}.png`}
                                                alt=""
                                                style={{
                                                    width: '32px',
                                                    height: '32px',
                                                    borderRadius: 'var(--radius-full)',
                                                    objectFit: 'cover',
                                                    background: 'var(--surface-2)',
                                                }}
                                                onError={(e) => {
                                                    (e.target as HTMLImageElement).style.display = 'none';
                                                }}
                                            />
                                            <span style={{ fontWeight: 500 }}>{player.name}</span>
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem' }}>{player.team_abbreviation}</td>
                                        <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                                            <span className="position-badge">{player.position?.charAt(0)}</span>
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontWeight: 500 }}>
                                            {player.season_ppg?.toFixed(1) || '-'}
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                                            {player.season_rpg?.toFixed(1) || '-'}
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                                            {player.season_apg?.toFixed(1) || '-'}
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                                            {player.season_mpg?.toFixed(1) || '-'}
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontWeight: 600, color: 'var(--hot)' }}>
                                            {player.fantasy_score?.toFixed(1) || '-'}
                                        </td>
                                    </tr>
                                </Link>
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
                }}>
                    <h3 style={{ margin: '0 0 0.5rem' }}>No players found</h3>
                    <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                        Try adjusting your filters or search criteria
                    </p>
                    <button
                        onClick={clearFilters}
                        style={{
                            marginTop: '1rem',
                            padding: '0.5rem 1rem',
                            background: 'var(--hot)',
                            border: 'none',
                            borderRadius: 'var(--radius-md)',
                            color: 'white',
                            cursor: 'pointer',
                        }}
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
                    gap: '0.5rem',
                    marginTop: '2rem',
                }}>
                    <button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                        style={{
                            padding: '0.5rem 1rem',
                            background: 'var(--surface-2)',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--radius-md)',
                            color: 'var(--text-primary)',
                            cursor: page === 1 ? 'not-allowed' : 'pointer',
                            opacity: page === 1 ? 0.5 : 1,
                        }}
                    >
                        Previous
                    </button>

                    <span style={{ padding: '0 1rem', color: 'var(--text-secondary)' }}>
                        Page {page} of {totalPages}
                    </span>

                    <button
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        style={{
                            padding: '0.5rem 1rem',
                            background: 'var(--surface-2)',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--radius-md)',
                            color: 'var(--text-primary)',
                            cursor: page === totalPages ? 'not-allowed' : 'pointer',
                            opacity: page === totalPages ? 0.5 : 1,
                        }}
                    >
                        Next
                    </button>
                </div>
            )}
        </div>
    );
}
