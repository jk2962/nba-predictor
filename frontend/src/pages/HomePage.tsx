/**
 * Home Page - Search and Top Performers
 * Shows player cards with faces, category filters, 12 per page with pagination
 */
import { useState, useEffect } from 'react';
import SearchBar from '../components/SearchBar';
import PlayerCard from '../components/PlayerCard';
import { LoadingState, ErrorState, EmptyState } from '../components/LoadingState';
import { playerApi, metricsApi } from '../services/api';
import type { TopPerformer, AllModelMetrics } from '../types';

const PLAYERS_PER_PAGE = 12;

export default function HomePage() {
    const [topPerformers, setTopPerformers] = useState<TopPerformer[]>([]);
    const [metrics, setMetrics] = useState<AllModelMetrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [sortBy, setSortBy] = useState<'fantasy' | 'points' | 'rebounds' | 'assists'>('fantasy');
    const [currentPage, setCurrentPage] = useState(0);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [performers, modelMetrics] = await Promise.all([
                playerApi.getTopPerformers({ limit: 50, stat: sortBy }),
                metricsApi.getMetrics().catch(() => null),
            ]);
            setTopPerformers(performers);
            setMetrics(modelMetrics);
            setCurrentPage(0); // Reset to first page when changing category
        } catch (err) {
            setError('Failed to load data. Make sure the backend is running.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [sortBy]);

    const totalPages = Math.ceil(topPerformers.length / PLAYERS_PER_PAGE);
    const paginatedPlayers = topPerformers.slice(
        currentPage * PLAYERS_PER_PAGE,
        (currentPage + 1) * PLAYERS_PER_PAGE
    );

    const goToNextPage = () => {
        if (currentPage < totalPages - 1) {
            setCurrentPage(currentPage + 1);
        }
    };

    const goToPreviousPage = () => {
        if (currentPage > 0) {
            setCurrentPage(currentPage - 1);
        }
    };

    return (
        <div className="container" style={{ padding: 'var(--space-2xl) var(--space-lg)' }}>
            {/* Hero Section */}
            <section style={{
                textAlign: 'center',
                marginBottom: 'var(--space-2xl)',
            }}>
                <h1 style={{
                    fontSize: '2.5rem',
                    fontWeight: 700,
                    marginBottom: 'var(--space-md)',
                    color: 'var(--text-primary)',
                    letterSpacing: '-0.03em',
                }}>
                    Performance Predictor
                </h1>
                <p style={{
                    fontSize: '1rem',
                    color: 'var(--text-secondary)',
                    maxWidth: '560px',
                    margin: '0 auto var(--space-xl)',
                    lineHeight: 1.5,
                }}>
                    AI-powered predictions for fantasy basketball. Search players, view stats,
                    and get next-game performance forecasts.
                </p>

                {/* Search Bar */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'center',
                    marginBottom: 'var(--space-xl)',
                }}>
                    <SearchBar placeholder="Search players..." />
                </div>

                {/* Model Metrics Badge */}
                {metrics && (
                    <div style={{
                        display: 'flex',
                        justifyContent: 'center',
                        gap: 'var(--space-md)',
                        flexWrap: 'wrap',
                    }}>
                        <MetricBadge
                            label="Points"
                            mae={metrics.points_model.mae}
                        />
                        <MetricBadge
                            label="Rebounds"
                            mae={metrics.rebounds_model.mae}
                        />
                        <MetricBadge
                            label="Assists"
                            mae={metrics.assists_model.mae}
                        />
                    </div>
                )}
            </section>

            {/* Top Performers Section */}
            <section>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: 'var(--space-lg)',
                    flexWrap: 'wrap',
                    gap: 'var(--space-md)',
                }}>
                    <h2 style={{
                        fontSize: '1.5rem',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        letterSpacing: '-0.02em',
                    }}>
                        Top Predicted Performers
                    </h2>

                    {/* Sort Filter */}
                    <div style={{
                        display: 'flex',
                        gap: 'var(--space-xs)',
                    }}>
                        {(['fantasy', 'points', 'rebounds', 'assists'] as const).map((stat) => (
                            <button
                                key={stat}
                                onClick={() => setSortBy(stat)}
                                className={sortBy === stat ? 'btn btn-primary' : 'btn btn-secondary'}
                                style={{
                                    textTransform: 'capitalize',
                                }}
                            >
                                {stat}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Content */}
                {loading ? (
                    <LoadingState message="Loading top performers..." />
                ) : error ? (
                    <ErrorState message={error} onRetry={fetchData} />
                ) : topPerformers.length === 0 ? (
                    <EmptyState
                        title="No predictions available"
                        description="Run the seed script to populate player data and train models."
                    />
                ) : (
                    <>
                        {/* Player Cards Grid */}
                        <div className="grid-players">
                            {paginatedPlayers.map((player, index) => (
                                <div
                                    key={player.player_id}
                                    className="animate-fadeIn"
                                    style={{ animationDelay: `${index * 0.05}s` }}
                                >
                                    <PlayerCard player={player} showPredictions statFilter={sortBy} />
                                </div>
                            ))}
                        </div>

                        {/* Pagination Controls */}
                        {totalPages > 1 && (
                            <div style={{
                                display: 'flex',
                                justifyContent: 'center',
                                alignItems: 'center',
                                gap: 'var(--space-lg)',
                                marginTop: 'var(--space-xl)',
                                paddingTop: 'var(--space-lg)',
                                borderTop: '1px solid var(--border-subtle)',
                            }}>
                                <button
                                    onClick={goToPreviousPage}
                                    disabled={currentPage === 0}
                                    className="btn btn-secondary"
                                >
                                    ← Previous
                                </button>

                                <span style={{
                                    fontSize: '0.875rem',
                                    color: 'var(--text-secondary)',
                                    fontVariantNumeric: 'tabular-nums',
                                }}>
                                    Page {currentPage + 1} of {totalPages}
                                </span>

                                <button
                                    onClick={goToNextPage}
                                    disabled={currentPage >= totalPages - 1}
                                    className="btn btn-secondary"
                                >
                                    Next →
                                </button>
                            </div>
                        )}
                    </>
                )}
            </section>
        </div>
    );
}

function MetricBadge({ label, mae }: { label: string; mae: number }) {
    const isGood = mae < 5;

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-sm)',
            padding: '0.5rem 1rem',
            background: 'var(--surface-2)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.8125rem',
        }}>
            <span style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: isGood ? 'var(--success)' : 'var(--warning)',
            }} />
            <span style={{
                color: 'var(--text-tertiary)',
                letterSpacing: '0.02em',
                textTransform: 'uppercase',
            }}>
                {label}
            </span>
            <span style={{
                fontWeight: 600,
                color: 'var(--text-primary)',
                fontVariantNumeric: 'tabular-nums',
            }}>
                {mae.toFixed(2)}
            </span>
            <span style={{
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
            }}>
                MAE
            </span>
        </div>
    );
}
