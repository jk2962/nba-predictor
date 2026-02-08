/**
 * Draft Helper Page - Live fantasy draft assistant
 */
import { useState, useEffect } from 'react';
import { LoadingState, ErrorState } from '../components/LoadingState';
import { draftApi } from '../services/api';

interface PlayerRanking {
    rank: number;
    player_name: string;
    position: string;
    position_rank: number;
    fantasy_points: number;
    vor: number;
    proj_points: number;
    proj_rebounds: number;
    proj_assists: number;
    proj_steals?: number;
    proj_blocks?: number;
    proj_turnovers?: number;
}

interface DraftRecommendation {
    recommended_player: string;
    rank: number;
    position: string;
    fantasy_points: number;
    vor: number;
    reasoning: string;
    alternatives: Array<{
        player_name: string;
        rank: number;
        position: string;
        fantasy_points: number;
    }>;
}

export default function DraftHelperPage() {
    const [rankings, setRankings] = useState<PlayerRanking[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [draftedPlayers, setDraftedPlayers] = useState<Set<string>>(new Set());
    const [myTeam, setMyTeam] = useState<Set<string>>(new Set());
    const [recommendation, setRecommendation] = useState<DraftRecommendation | null>(null);
    const [showRecommendation, setShowRecommendation] = useState(false);
    const [showInactive, setShowInactive] = useState(false);

    useEffect(() => {
        fetchRankings();
    }, [showInactive]);

    const fetchRankings = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await draftApi.getDraftRankings(12, showInactive);
            setRankings(data.rankings);
        } catch (err) {
            setError('Failed to load rankings');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const getRecommendation = async () => {
        try {
            const rec = await draftApi.getDraftRecommendation(
                Array.from(draftedPlayers),
                Array.from(myTeam)
            );
            setRecommendation(rec);
            setShowRecommendation(true);
        } catch (err) {
            console.error('Failed to get recommendation:', err);
        }
    };

    const toggleDrafted = (playerName: string) => {
        setDraftedPlayers(prev => {
            const newSet = new Set(prev);
            if (newSet.has(playerName)) {
                newSet.delete(playerName);
                // Also remove from my team if un-drafting
                setMyTeam(mt => {
                    const newMt = new Set(mt);
                    newMt.delete(playerName);
                    return newMt;
                });
            } else {
                newSet.add(playerName);
            }
            return newSet;
        });
        setShowRecommendation(false); // Hide recommendation when draft state changes
    };

    const toggleMyTeam = (playerName: string) => {
        if (!draftedPlayers.has(playerName)) {
            // Auto-draft if not already drafted
            setDraftedPlayers(prev => new Set(prev).add(playerName));
        }

        setMyTeam(prev => {
            const newSet = new Set(prev);
            if (newSet.has(playerName)) {
                newSet.delete(playerName);
            } else {
                newSet.add(playerName);
            }
            return newSet;
        });
        setShowRecommendation(false);
    };

    const clearDraft = () => {
        setDraftedPlayers(new Set());
        setMyTeam(new Set());
        setRecommendation(null);
        setShowRecommendation(false);
    };

    const availablePlayers = rankings.filter(p => !draftedPlayers.has(p.player_name));

    if (loading) return <LoadingState />;
    if (error) return <ErrorState message={error} />;

    return (
        <div className="container" style={{ padding: '2rem 1.5rem', maxWidth: '1400px' }}>
            {/* Header */}
            <header style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                        <h1 style={{
                            fontSize: '2rem',
                            fontWeight: 700,
                            marginBottom: '0.5rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                        }}>
                            <span>📋</span>
                            Fantasy Draft Helper
                        </h1>
                        <p style={{ color: 'var(--color-text-secondary)' }}>
                            Ranked by projected fantasy value with VOR (Value Over Replacement).
                            Track your live draft and get smart recommendations.
                        </p>
                    </div>

                    <label style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        cursor: 'pointer',
                        padding: '0.5rem 1rem',
                        background: 'var(--color-surface)',
                        border: '1px solid var(--color-border)',
                        borderRadius: '8px',
                        fontSize: '0.875rem',
                        fontWeight: 500,
                    }}>
                        <input
                            type="checkbox"
                            checked={showInactive}
                            onChange={(e) => setShowInactive(e.target.checked)}
                            style={{ accentColor: 'var(--color-primary)' }}
                        />
                        Show Inactive Players
                    </label>
                </div>
            </header>

            {/* Draft Controls */}
            <div style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: '12px',
                padding: '1.5rem',
                marginBottom: '1.5rem',
            }}>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '1rem',
                }}>
                    <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
                        <div>
                            <div style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>
                                Total Drafted
                            </div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-primary)' }}>
                                {draftedPlayers.size}
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>
                                My Team
                            </div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-success)' }}>
                                {myTeam.size}
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>
                                Available
                            </div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>
                                {availablePlayers.length}
                            </div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <button
                            onClick={getRecommendation}
                            disabled={draftedPlayers.size === rankings.length}
                            style={{
                                padding: '0.625rem 1.25rem',
                                background: 'linear-gradient(135deg, var(--color-primary), var(--color-accent))',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                fontWeight: 600,
                                cursor: draftedPlayers.size === rankings.length ? 'not-allowed' : 'pointer',
                                opacity: draftedPlayers.size === rankings.length ? 0.5 : 1,
                                transition: 'transform 0.2s',
                            }}
                            onMouseEnter={(e) => {
                                if (draftedPlayers.size < rankings.length) {
                                    e.currentTarget.style.transform = 'scale(1.05)';
                                }
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.transform = 'scale(1)';
                            }}
                        >
                            🎯 Who Should I Draft?
                        </button>
                        <button
                            onClick={clearDraft}
                            disabled={draftedPlayers.size === 0}
                            style={{
                                padding: '0.625rem 1.25rem',
                                background: 'var(--color-surface)',
                                color: 'var(--color-text)',
                                border: '1px solid var(--color-border)',
                                borderRadius: '8px',
                                fontWeight: 600,
                                cursor: draftedPlayers.size === 0 ? 'not-allowed' : 'pointer',
                                opacity: draftedPlayers.size === 0 ? 0.5 : 1,
                            }}
                        >
                            Clear Draft
                        </button>
                        <button
                            onClick={() => draftApi.exportRankings()}
                            style={{
                                padding: '0.625rem 1.25rem',
                                background: 'var(--color-surface)',
                                color: 'var(--color-text)',
                                border: '1px solid var(--color-border)',
                                borderRadius: '8px',
                                fontWeight: 600,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                            }}
                        >
                            <span>⬇️</span> Export CSV
                        </button>
                    </div>
                </div>
            </div>

            {/* Recommendation Card */}
            {showRecommendation && recommendation && (
                <div style={{
                    background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.1))',
                    border: '2px solid var(--color-primary)',
                    borderRadius: '12px',
                    padding: '1.5rem',
                    marginBottom: '1.5rem',
                    position: 'relative',
                }}>
                    <button
                        onClick={() => setShowRecommendation(false)}
                        style={{
                            position: 'absolute',
                            top: '1rem',
                            right: '1rem',
                            background: 'none',
                            border: 'none',
                            fontSize: '1.5rem',
                            cursor: 'pointer',
                            opacity: 0.6,
                            transition: 'opacity 0.2s',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                        onMouseLeave={(e) => e.currentTarget.style.opacity = '0.6'}
                    >
                        ×
                    </button>

                    <h3 style={{ fontSize: '1.125rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span>🎯</span>
                        Draft Recommendation
                    </h3>

                    <div style={{
                        background: 'var(--color-surface)',
                        borderRadius: '8px',
                        padding: '1.25rem',
                        marginBottom: '1rem',
                    }}>
                        <div style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                            {recommendation.recommended_player}
                        </div>
                        <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                            <div>
                                <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>Rank: </span>
                                <span style={{ fontWeight: 600 }}>#{recommendation.rank}</span>
                            </div>
                            <div>
                                <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>Fantasy Pts: </span>
                                <span style={{ fontWeight: 600, color: 'var(--color-primary)' }}>{recommendation.fantasy_points}</span>
                            </div>
                            <div>
                                <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>VOR: </span>
                                <span style={{ fontWeight: 600, color: 'var(--color-success)' }}>+{recommendation.vor}</span>
                            </div>
                        </div>
                        <div style={{
                            color: 'var(--color-text-secondary)',
                            fontSize: '0.9375rem',
                            fontStyle: 'italic',
                        }}>
                            {recommendation.reasoning}
                        </div>
                    </div>

                    {recommendation.alternatives && recommendation.alternatives.length > 0 && (
                        <div>
                            <div style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-text-secondary)' }}>
                                Also Consider:
                            </div>
                            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                                {recommendation.alternatives.map((alt, i) => (
                                    <div
                                        key={i}
                                        style={{
                                            background: 'var(--color-surface)',
                                            border: '1px solid var(--color-border)',
                                            borderRadius: '8px',
                                            padding: '0.75rem',
                                            flex: '1 1 200px',
                                        }}
                                    >
                                        <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                                            {alt.player_name}
                                        </div>
                                        <div style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                                            #{alt.rank} • {alt.fantasy_points} fpts
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Rankings Table */}
            <div style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: '12px',
                overflow: 'hidden',
            }}>
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ background: 'var(--color-background)', borderBottom: '1px solid var(--color-border)' }}>
                                <th style={{ padding: '1rem', textAlign: 'center', width: '60px' }}>Drafted</th>
                                <th style={{ padding: '1rem', textAlign: 'center', width: '60px' }}>Mine</th>
                                <th style={{ padding: '1rem', textAlign: 'left', width: '60px' }}>Rank</th>
                                <th style={{ padding: '1rem', textAlign: 'left' }}>Player</th>
                                <th style={{ padding: '1rem', textAlign: 'center' }}>Fantasy Pts</th>
                                <th style={{ padding: '1rem', textAlign: 'center' }}>VOR</th>
                                <th style={{ padding: '1rem', textAlign: 'center' }}>PPG</th>
                                <th style={{ padding: '1rem', textAlign: 'center' }}>RPG</th>
                                <th style={{ padding: '1rem', textAlign: 'center' }}>APG</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rankings.map((player, idx) => {
                                const isDrafted = draftedPlayers.has(player.player_name);
                                const isMine = myTeam.has(player.player_name);

                                return (
                                    <tr
                                        key={idx}
                                        style={{
                                            borderBottom: '1px solid var(--color-border)',
                                            background: isMine
                                                ? 'rgba(34, 197, 94, 0.1)'
                                                : isDrafted
                                                    ? 'rgba(156, 163, 175, 0.1)'
                                                    : 'transparent',
                                            opacity: isDrafted && !isMine ? 0.5 : 1,
                                        }}
                                    >
                                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                                            <input
                                                type="checkbox"
                                                checked={isDrafted}
                                                onChange={() => toggleDrafted(player.player_name)}
                                                style={{
                                                    width: '18px',
                                                    height: '18px',
                                                    cursor: 'pointer',
                                                    accentColor: 'var(--color-primary)',
                                                }}
                                            />
                                        </td>
                                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                                            <input
                                                type="checkbox"
                                                checked={isMine}
                                                onChange={() => toggleMyTeam(player.player_name)}
                                                style={{
                                                    width: '18px',
                                                    height: '18px',
                                                    cursor: 'pointer',
                                                    accentColor: 'var(--color-success)',
                                                }}
                                            />
                                        </td>
                                        <td style={{ padding: '1rem', fontWeight: 700 }}>
                                            {player.rank}
                                        </td>
                                        <td style={{ padding: '1rem' }}>
                                            <div style={{ fontWeight: 600 }}>
                                                {player.player_name}
                                            </div>
                                        </td>
                                        <td style={{ padding: '1rem', textAlign: 'center', fontWeight: 700, color: 'var(--color-primary)' }}>
                                            {player.fantasy_points}
                                        </td>
                                        <td style={{
                                            padding: '1rem',
                                            textAlign: 'center',
                                            fontWeight: 600,
                                            color: player.vor > 0 ? 'var(--color-success)' : 'var(--color-text-secondary)',
                                        }}>
                                            {player.vor > 0 ? '+' : ''}{player.vor}
                                        </td>
                                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                                            {player.proj_points}
                                        </td>
                                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                                            {player.proj_rebounds}
                                        </td>
                                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                                            {player.proj_assists}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Legend */}
            <div style={{
                marginTop: '1.5rem',
                padding: '1rem',
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                fontSize: '0.875rem',
                color: 'var(--color-text-secondary)',
            }}>
                <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>How to Use:</div>
                <ul style={{ margin: 0, paddingLeft: '1.5rem', lineHeight: 1.6 }}>
                    <li><strong>Drafted</strong> - Check players as they get drafted (by anyone)</li>
                    <li><strong>Mine</strong> - Mark players on your team (auto-marks as drafted)</li>
                    <li><strong>VOR</strong> - Value Over Replacement (higher is better)</li>
                    <li><strong>Recommendation</strong> - Click "Who Should I Draft?" for smart suggestions</li>
                </ul>
            </div>
        </div>
    );
}
