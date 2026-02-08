/**
 * Search Bar Component with Autocomplete
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { playerApi } from '../services/api';
import type { PlayerSearchResult } from '../types';

interface SearchBarProps {
    placeholder?: string;
    onSelect?: (player: PlayerSearchResult) => void;
    autoNavigate?: boolean;
}

export default function SearchBar({
    placeholder = 'Search NBA players...',
    onSelect,
    autoNavigate = true,
}: SearchBarProps) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<PlayerSearchResult[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isOpen, setIsOpen] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const inputRef = useRef<HTMLInputElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const navigate = useNavigate();

    // Debounced search
    useEffect(() => {
        if (query.length < 2) {
            setResults([]);
            setIsOpen(false);
            return;
        }

        const timer = setTimeout(async () => {
            setIsLoading(true);
            try {
                const data = await playerApi.searchPlayers(query);
                setResults(data);
                setIsOpen(data.length > 0);
                setSelectedIndex(-1);
            } catch (error) {
                console.error('Search error:', error);
                setResults([]);
            } finally {
                setIsLoading(false);
            }
        }, 300);

        return () => clearTimeout(timer);
    }, [query]);

    // Click outside to close
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target as Node) &&
                !inputRef.current?.contains(event.target as Node)
            ) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelect = (player: PlayerSearchResult) => {
        setQuery('');
        setIsOpen(false);

        if (onSelect) {
            onSelect(player);
        }

        if (autoNavigate) {
            navigate(`/player/${player.id}`);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!isOpen) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setSelectedIndex((prev) =>
                    prev < results.length - 1 ? prev + 1 : prev
                );
                break;
            case 'ArrowUp':
                e.preventDefault();
                setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
                break;
            case 'Enter':
                e.preventDefault();
                if (selectedIndex >= 0 && results[selectedIndex]) {
                    handleSelect(results[selectedIndex]);
                }
                break;
            case 'Escape':
                setIsOpen(false);
                break;
        }
    };

    return (
        <div style={{ position: 'relative', width: '100%', maxWidth: '500px' }}>
            {/* Input */}
            <div style={{ position: 'relative' }}>
                <input
                    ref={inputRef}
                    type="text"
                    className="input"
                    placeholder={placeholder}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => query.length >= 2 && results.length > 0 && setIsOpen(true)}
                    onKeyDown={handleKeyDown}
                    style={{
                        paddingLeft: '3rem',
                        paddingRight: isLoading ? '3rem' : '1rem',
                    }}
                />

                {/* Search Icon */}
                <span style={{
                    position: 'absolute',
                    left: '1rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    fontSize: '1.25rem',
                    opacity: 0.5,
                }}>
                    🔍
                </span>

                {/* Loading Spinner */}
                {isLoading && (
                    <div style={{
                        position: 'absolute',
                        right: '1rem',
                        top: '50%',
                        transform: 'translateY(-50%)',
                    }}>
                        <div className="spinner" style={{ width: '20px', height: '20px' }} />
                    </div>
                )}
            </div>

            {/* Dropdown */}
            {isOpen && (
                <div
                    ref={dropdownRef}
                    className="card"
                    style={{
                        position: 'absolute',
                        top: 'calc(100% + 0.5rem)',
                        left: 0,
                        right: 0,
                        maxHeight: '400px',
                        overflowY: 'auto',
                        padding: '0.5rem',
                        zIndex: 100,
                    }}
                >
                    {results.map((player, index) => (
                        <div
                            key={player.id}
                            onClick={() => handleSelect(player)}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                padding: '0.75rem',
                                borderRadius: '0.5rem',
                                cursor: 'pointer',
                                background: index === selectedIndex
                                    ? 'rgba(99, 102, 241, 0.2)'
                                    : 'transparent',
                                transition: 'background 0.15s ease',
                            }}
                            onMouseEnter={() => setSelectedIndex(index)}
                        >
                            {/* Avatar */}
                            <div style={{
                                width: '40px',
                                height: '40px',
                                borderRadius: '0.5rem',
                                overflow: 'hidden',
                                background: 'var(--color-bg-tertiary)',
                                flexShrink: 0,
                            }}>
                                {player.headshot_url ? (
                                    <img
                                        src={player.headshot_url}
                                        alt={player.name}
                                        style={{
                                            width: '100%',
                                            height: '100%',
                                            objectFit: 'cover',
                                        }}
                                        onError={(e) => {
                                            (e.target as HTMLImageElement).style.display = 'none';
                                        }}
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

                            {/* Info */}
                            <div style={{ flex: 1 }}>
                                <div style={{
                                    fontWeight: 500,
                                    color: 'var(--color-text-primary)',
                                }}>
                                    {player.name}
                                </div>
                                <div style={{
                                    fontSize: '0.8rem',
                                    color: 'var(--color-text-secondary)',
                                }}>
                                    {player.team_abbreviation} • {player.position}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
