from .structured_queries import (
    get_matches_by_surface,
    get_win_loss_summary,
    get_tournaments,
    get_ranking_summary,
)

print("\n=== Matches on Hard ===")
print(get_matches_by_surface("hard"))

print("\n=== Win/Loss Summary ===")
print(get_win_loss_summary())

print("\n=== Tournaments ===")
print(get_tournaments())

print("\n=== Ranking Summary ===")
print(get_ranking_summary())