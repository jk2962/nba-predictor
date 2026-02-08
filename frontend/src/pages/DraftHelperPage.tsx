/**
 * Draft Helper Page - Ranked player list for fantasy drafts
 */
import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { LoadingState, ErrorState, EmptyState } from '../components/LoadingState';
import { playerApi } from '../services/api';
import type { Player } from '../types';

type SortField = 'name' | 'ppg' | 'rpg' | 'apg' | 'fantasy';
type SortDirection = 'asc' | 'desc';

export default function DraftHelperPage() {
    const [players, setPlayers] = useState<Player[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [positionFilter, setPositionFilter] = useState<string>('all');
    const [sortField, setSortField] = useState<SortField>('fantasy');
    const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
    const [page, setPage] = useState(1);
    const perPage = 50;

    useEffect(() => {
        const fetchPlayers = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await playerApi.getPlayers({
                    page: 1,
                    per_page: 200,
                    position: positionFilter !== 'all' ? positionFilter : undefined,
                });
                setPlayers(response.items);
            } catch (err) {
                setError('Failed to load players');
            } finally {
                setLoading(false);
            }
        };

        fetchPlayers();
    }, [positionFilter]);

    // Calculate fantasy score and sort
    const sortedPlayers = useMemo(() => {
        const playersWithFantasy = players.map(p => ({
            ...p,
            fantasy: (p.season_ppg || 0) + 1.2 * (p.season_rpg || 0) + 1.5 * (p.season_apg || 0),
        }));

        return playersWithFantasy.sort((a, b) => {
            let aVal: number | string;
            let bVal: number | string;

            switch (sortField) {
                case 'name':
                    aVal = a.name;
                    bVal = b.name;
                    break;
                case 'ppg':
                    aVal = a.season_ppg || 0;
                    bVal = b.season_ppg || 0;
                    break;
                case 'rpg':
                    aVal = a.season_rpg || 0;
                    bVal = b.season_rpg || 0;
                    break;
                case 'apg':
                    aVal = a.season_apg || 0;
                    bVal = b.season_apg || 0;
                    break;
                case 'fantasy':
                default:
                    aVal = a.fantasy;
                    bVal = b.fantasy;
                    break;
            }

            if (typeof aVal === 'string' && typeof bVal === 'string') {
                return sortDirection === 'asc'
                    ? aVal.localeCompare(bVal)
                    : bVal.localeCompare(aVal);
            }

            return sortDirection === 'asc'
                ? (aVal as number) - (bVal as number)
                : (bVal as number) - (aVal as number);
        });
    }, [players, sortField, sortDirection]);

    // Pagination
    const paginatedPlayers = sortedPlayers.slice(
        (page - 1) * perPage,
        page * perPage
    );
    const totalPages = Math.ceil(sortedPlayers.length / perPage);

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('desc');
        }
    };

    const SortHeader = ({ field, label }: { field: SortField; label: string }) => (
        <th
            onClick={() => handleSort(field)}
            style={{ cursor: 'pointer', userSelect: 'none' }}
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {label}
                {sortField === field && (
                    <span style={{ opacity: 0.7 }}>
                        {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                )}
            </div>
        </th>
    );

    return (
        <div className="container" style={{ padding: '2rem 1.5rem' }}>
            {/* Header */}
            <header style={{ marginBottom: '2rem' }}>
                <h1 style={{
                    fontSize: '2rem',
                    fontWeight: 700,
                    marginBottom: '0.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                }}>
                    <span>📋</span>
                    Draft Helper
                </h1>
                <p style={{ color: 'var(--color-text-secondary)' }}>
                    Ranked player list by projected fantasy value. Click columns to sort.
                </p>
            </header>

            {/* Filters */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1.5rem',
                flexWrap: 'wrap',
                gap: '1rem',
            }}>
                {/* Position Filter */}
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {['all', 'G', 'F', 'C'].map((pos) => (
                        <button
                            key={pos}
                            onClick={() => setPositionFilter(pos)}
                            className={positionFilter === pos ? 'btn btn-primary' : 'btn btn-secondary'}
                            style={{
                                padding: '0.5rem 1rem',
                                fontSize: '0.85rem',
                            }}
                        >
                            {pos === 'all' ? 'All Positions' : pos}
                        </button>
                    ))}
                </div>

                {/* Results count */}
                <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                    {sortedPlayers.length} players
                </div>
            </div>

            {/* Content */}
            {loading ? (
                <LoadingState message="Loading players..." />
            ) : error ? (
                <ErrorState message={error} />
            ) : sortedPlayers.length === 0 ? (
                <EmptyState
                    title="No players found"
                    description="Run the seed script to populate player data."
                    icon="📋"
                />
            ) : (
                <>
                    {/* Table */}
                    <div className="card" style={{ overflow: 'hidden' }}>
                        <div style={{ overflowX: 'auto' }}>
                            <table className="table">
                                <thead>
                                    <tr>
                                        <th style={{ width: '60px' }}>Rank</th>
                                        <SortHeader field="name" label="Player" />
                                        <th>Team</th>
                                        <th>Pos</th>
                                        <SortHeader field="ppg" label="PPG" />
                                        <SortHeader field="rpg" label="RPG" />
                                        <SortHeader field="apg" label="APG" />
                                        <SortHeader field="fantasy" label="Fantasy" />
                                    </tr>
                                </thead>
                                <tbody>
                                    {paginatedPlayers.map((player, index) => {
                                        const rank = (page - 1) * perPage + index + 1;
                                        return (
                                            <tr key={player.id}>
                                                <td>
                                                    <span style={{
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        width: '32px',
                                                        height: '32px',
                                                        borderRadius: '0.5rem',
                                                        background: rank <= 10
                                                            ? 'var(--gradient-primary)'
                                                            : 'var(--color-bg-tertiary)',
                                                        fontWeight: 600,
                                                        fontSize: '0.85rem',
                                                    }}>
                                                        {rank}
                                                    </span>
                                                </td>
                                                <td>
                                                    <Link
                                                        to={`/player/${player.id}`}
                                                        style={{
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '0.75rem',
                                                            color: 'var(--color-text-primary)',
                                                        }}
                                                    >
                                                        <div style={{
                                                            width: '36px',
                                                            height: '36px',
                                                            borderRadius: '0.5rem',
                                                            overflow: 'hidden',
                                                            background: 'var(--color-bg-tertiary)',
                                                            flexShrink: 0,
                                                        }}>
                                                            {player.headshot_url ? (
                                                                <img
                                                                    src={player.headshot_url}
                                                                    alt=""
                                                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                                                />
                                                            ) : (
                                                                <div style={{
                                                                    width: '100%',
                                                                    height: '100%',
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    justifyContent: 'center',
                                                                }}>
                                                                    🏀
                                                                </div>
                                                            )}
                                                        </div>
                                                        <span style={{ fontWeight: 500 }}>{player.name}</span>
                                                    </Link>
                                                </td>
                                                <td>{player.team_abbreviation || '-'}</td>
                                                <td>
                                                    {player.position && (
                                                        <span className={`position-badge position-${player.position.charAt(0)}`}>
                                                            {player.position.charAt(0)}
                                                        </span>
                                                    )}
                                                </td>
                                                <td style={{ fontWeight: 600, color: '#6366f1' }}>
                                                    {player.season_ppg?.toFixed(1) || '-'}
                                                </td>
                                                <td style={{ fontWeight: 600, color: '#22c55e' }}>
                                                    {player.season_rpg?.toFixed(1) || '-'}
                                                </td>
                                                <td style={{ fontWeight: 600, color: '#f97316' }}>
                                                    {player.season_apg?.toFixed(1) || '-'}
                                                </td>
                                                <td>
                                                    <div style={{
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        padding: '0.25rem 0.75rem',
                                                        background: 'var(--gradient-primary)',
                                                        borderRadius: '1rem',
                                                        fontWeight: 600,
                                                    }}>
                                                        {(player as any).fantasy.toFixed(1)}
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div style={{
                            display: 'flex',
                            justifyContent: 'center',
                            gap: '0.5rem',
                            marginTop: '1.5rem',
                        }}>
                            <button
                                className="btn btn-secondary"
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page === 1}
                                style={{ opacity: page === 1 ? 0.5 : 1 }}
                            >
                                Previous
                            </button>
                            <span style={{
                                display: 'flex',
                                alignItems: 'center',
                                padding: '0 1rem',
                                color: 'var(--color-text-secondary)',
                            }}>
                                Page {page} of {totalPages}
                            </span>
                            <button
                                className="btn btn-secondary"
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                disabled={page === totalPages}
                                style={{ opacity: page === totalPages ? 0.5 : 1 }}
                            >
                                Next
                            </button>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
