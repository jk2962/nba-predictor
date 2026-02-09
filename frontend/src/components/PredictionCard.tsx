/**
 * Prediction Card Component
 */
import { useState } from 'react';
import type { PredictionResult } from '../types';

// Z-scores for different confidence levels
const CI_OPTIONS = [
    { label: '50%', value: 0.50, z: 0.674 },
    { label: '68%', value: 0.68, z: 1.0 },
    { label: '80%', value: 0.80, z: 1.282 },
    { label: '90%', value: 0.90, z: 1.645 },
    { label: '95%', value: 0.95, z: 1.96 },
    { label: '99%', value: 0.99, z: 2.576 },
];

interface PredictionCardProps {
    prediction: PredictionResult;
    showConfidence?: boolean;
}

export default function PredictionCard({
    prediction,
    showConfidence = true
}: PredictionCardProps) {
    const [selectedCI, setSelectedCI] = useState(0.95);

    const currentCIOption = CI_OPTIONS.find(opt => opt.value === selectedCI) || CI_OPTIONS[4];

    return (
        <div className="card" style={{ padding: 'var(--space-lg)' }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 'var(--space-lg)',
                flexWrap: 'wrap',
                gap: 'var(--space-sm)',
            }}>
                <h3 style={{
                    fontSize: '1.125rem',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    letterSpacing: '-0.01em',
                }}>
                    Next Game Prediction
                </h3>

                {/* CI Selector */}
                {showConfidence && (
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--space-xs)',
                    }}>
                        <span style={{
                            fontSize: '0.75rem',
                            color: 'var(--text-tertiary)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.02em',
                        }}>
                            CI:
                        </span>
                        <div style={{
                            display: 'flex',
                            gap: '2px',
                            background: 'var(--surface-1)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '2px',
                            border: '1px solid var(--border)',
                        }}>
                            {CI_OPTIONS.map((option) => (
                                <button
                                    key={option.value}
                                    onClick={() => setSelectedCI(option.value)}
                                    style={{
                                        padding: '0.25rem 0.5rem',
                                        fontSize: '0.6875rem',
                                        fontWeight: selectedCI === option.value ? 600 : 400,
                                        color: selectedCI === option.value ? 'white' : 'var(--text-tertiary)',
                                        background: selectedCI === option.value ? 'var(--hot)' : 'transparent',
                                        border: 'none',
                                        borderRadius: 'var(--radius-sm)',
                                        cursor: 'pointer',
                                        transition: 'all 0.15s ease',
                                    }}
                                >
                                    {option.label}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {prediction.opponent_team && (
                <div style={{
                    fontSize: '0.8125rem',
                    color: 'var(--text-tertiary)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.02em',
                    marginBottom: 'var(--space-md)',
                    marginTop: 'calc(-1 * var(--space-sm))',
                }}>
                    vs {prediction.opponent_team} {prediction.is_home ? '(Home)' : '(Away)'}
                </div>
            )}

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 'var(--space-md)',
            }}>
                <PredictionStat
                    label="Points"
                    value={prediction.predicted_points}
                    lower95={prediction.points_lower}
                    upper95={prediction.points_upper}
                    showConfidence={showConfidence}
                    selectedCI={currentCIOption}
                />
                <PredictionStat
                    label="Rebounds"
                    value={prediction.predicted_rebounds}
                    lower95={prediction.rebounds_lower}
                    upper95={prediction.rebounds_upper}
                    showConfidence={showConfidence}
                    selectedCI={currentCIOption}
                />
                <PredictionStat
                    label="Assists"
                    value={prediction.predicted_assists}
                    lower95={prediction.assists_lower}
                    upper95={prediction.assists_upper}
                    showConfidence={showConfidence}
                    selectedCI={currentCIOption}
                />
            </div>

            {prediction.fantasy_score && (
                <div style={{
                    marginTop: 'var(--space-lg)',
                    paddingTop: 'var(--space-lg)',
                    borderTop: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'baseline',
                    gap: 'var(--space-sm)',
                }}>
                    <div className="data-label">
                        Projected Fantasy
                    </div>
                    <div className="data-primary" style={{
                        color: 'var(--hot)',
                    }}>
                        {prediction.fantasy_score.toFixed(1)}
                    </div>
                </div>
            )}
        </div>
    );
}

function PredictionStat({
    label,
    value,
    lower95: _lower95,
    upper95,
    showConfidence,
    selectedCI,
}: {
    label: string;
    value: number;
    lower95: number;
    upper95: number;
    showConfidence: boolean;
    selectedCI: { label: string; value: number; z: number };
}) {
    // Calculate the standard deviation from the 95% CI
    // CI = value ± z * std, so std = (upper - value) / 1.96
    const std = (upper95 - value) / 1.96;

    // Recalculate bounds for the selected CI
    const lower = Math.max(0, value - selectedCI.z * std);
    const upper = value + selectedCI.z * std;

    // Calculate confidence width based on range relative to value
    const range = upper - lower;
    const confidenceWidth = Math.max(20, Math.min(100, 100 - (range / value) * 50));

    return (
        <div style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-md)',
            textAlign: 'center',
        }}>
            <div className="data-label" style={{
                marginBottom: 'var(--space-sm)',
            }}>
                {label}
            </div>

            <div className="data-primary" style={{
                color: 'var(--hot)',
                marginBottom: 'var(--space-sm)',
            }}>
                {value.toFixed(1)}
            </div>

            {showConfidence && (
                <>
                    <div style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-tertiary)',
                        marginBottom: 'var(--space-sm)',
                        fontVariantNumeric: 'tabular-nums',
                    }}>
                        {lower.toFixed(1)} - {upper.toFixed(1)}
                    </div>

                    <div className="confidence-bar">
                        <div
                            className="confidence-bar-fill"
                            style={{
                                width: `${confidenceWidth}%`,
                            }}
                        />
                    </div>
                    <div style={{
                        fontSize: '0.6875rem',
                        color: 'var(--text-muted)',
                        marginTop: 'var(--space-xs)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.02em',
                    }}>
                        {selectedCI.label} Confidence
                    </div>
                </>
            )}
        </div>
    );
}

