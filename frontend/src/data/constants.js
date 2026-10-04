export const PROFILE_IMG =
  'https://lh3.googleusercontent.com/aida-public/AB6AXuDw26tQxMLFKea_DMVHSGhmH6yYNHHMOn97-n-tyjTXty1kn8qbRuW3QztbkwYJ8rUg0BZHP8RxbnhsCbg4WKvzkRxXRqHFz0glIkvwBQeZiv9K-I-cPIWa0kzAXmT93xTMaxUlxrV3o17EKRXvDVRHa63CYjbJgk_iVn1O7zzV_4Hz7hqwJC0F3iIOD11W_YOXyAUBwdHWSPQF5G3GoMiI1zG4s06t_DIOf27zAcSXh4YWtHGOC80P1ghHd9l63jcmlHXLiaFkhw'

export const NAV_ITEMS = [
  // { id: 'dashboard', icon: 'dashboard', label: 'Dashboard', path: '/dashboard' }, 
  // { id: 'data-portal', icon: 'analytics', label: 'Data Portal', path: '/data-portal' }, 
  { id: 'media-library', icon: 'video_library', label: 'Media Library', path: '/media-library' },
  { id: 'ai-chatbot', icon: 'psychology', label: 'AI Insights', path: '/ai-chatbot' },
  // { id: 'archive', icon: 'inventory_2', label: 'Archive', path: '/archive' }, 
]

export const DASHBOARD_STATS = [
  { label: 'Matches Played', value: '124', subtext: '↑ 12% vs last season', icon: 'sports_tennis', subtextIcon: 'trending_up', subtextColor: 'text-primary' },
  { label: 'Performance Score', value: '92.4', subtext: 'Top 5% of league', icon: 'bolt', subtextColor: 'text-primary-container' },
  { label: 'Videos Analyzed', value: '1,052', subtext: '45 hours total footage', icon: 'movie', subtextColor: 'text-muted-foreground' },
  { label: 'AI Queries', value: '348', subtext: 'Insights generated today', icon: 'chat_bubble', subtextColor: 'text-primary' },
]

export const WIN_RATES = [
  { surface: 'CLAY', pct: 78, color: 'bg-primary' },
  { surface: 'GRASS', pct: 64, color: 'bg-primary' },
  { surface: 'HARD COURT', pct: 89, color: 'bg-primary-container' },
  { surface: 'INDOOR', pct: 52, color: 'bg-secondary' },
]

export const RECENT_VIDEOS = [
  {
    title: 'Quarter Final: serve mechanics',
    time: '2 hours ago • 4m 12s',
    img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDsI6hAbe-eRF3e1toDzfdqH7xTO8icZ5wztYEH1z85dWqbhgrhxV0wSml5TM3Jm3F3jGrPN-hMwljETJIaMHchrIxCq4Kx9H7nVuClcQx-Brdx_8Tiu9K6lGm1lsB4A67lOWh5rviDe-pIZyJloiTRISP6UJlh9hb74kzRdHYfBe78Knu7CjNhI9nTXHZYqfVjQUqdBS5eloG4Ozd-4R6JnKejAtfFjmTuP-7Edd4ZAEmk0XBbHHHG4NJuXCKJqy6AU7dVXEwZGA',
  },
  {
    title: 'Baseline Movement Analysis',
    time: '5 hours ago • 12m 45s',
    img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBbLEOo4FEt9wxQc5C-J02aIS9w-OdnSZ8IXPclLd20CDtNc3o8xk30_YgaXRt-3-aXTwnyGWJuBlvp0UQx_e4UKp-FYlZyDdyapwiwj0DBq9oVyjjrbl6zbPgzcBZ3I2ub2bl8M52eZPKNEkZs_zW6Sq4XY-S6meZxGu00CxuRPc-TWD0N1asgn3jaoigtLjzOwFOoRDYTULveOccfDbwOOdd28i0CVX-A36aWg8EiYN9A4prV3yAp4lFcp8oaPzi7JpMheICPWA',
  },
]

export const RECENT_QUERIES = [
  { query: '"Compare win rates on second serves against top 10 opponents in the last 12 months."', status: 'AI Report Generated' },
  { query: '"Identify unforced error patterns in the backhand wing during long rallies."', status: 'Visual Heatmap Ready' },
]

export const MATCH_DATA = [
  { player: 'Carlos Alcaraz', opponent: 'Novak Djokovic', date: 'Jul 14, 2024', score: '6-2, 6-2, 7-6', aces: 12, df: 3 },
  { player: 'Jannik Sinner', opponent: 'Daniil Medvedev', date: 'Jul 09, 2024', score: '3-6, 6-3, 7-6, 6-1', aces: 15, df: 5 },
  { player: 'Novak Djokovic', opponent: 'Lorenzo Musetti', date: 'Jul 12, 2024', score: '6-4, 7-6, 6-4', aces: 9, df: 2 },
  { player: 'Daniil Medvedev', opponent: 'Tommy Paul', date: 'Jul 07, 2024', score: '6-4, 6-2, 6-3', aces: 11, df: 7 },
  { player: 'Taylor Fritz', opponent: 'Alexander Zverev', date: 'Jul 08, 2024', score: '4-6, 6-7, 6-4, 7-6, 6-3', aces: 22, df: 4 },
  { player: 'Lorenzo Musetti', opponent: 'Taylor Fritz', date: 'Jul 10, 2024', score: '3-6, 7-6, 6-2, 3-6, 6-1', aces: 7, df: 3 },
]

export const MEDIA_ITEMS = [
  { type: 'video', title: 'Serve Mechanics - Final.mp4', size: '12.4 MB • Oct 24', duration: '04:22', selected: true, img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuD8FC5Ny-AtWPS3a3r5tPglEwItn6hq6e0HzHPs4T91jOC5-2AdgsNOA9X8ATjj0KYvbHh3IkeAReKFoLVyl83ugd7bnvnrkPZTNuf6Z1xJPbk8B1HFat9VLDq2iIzwix58AKqDGtmMST_mF_a5AcbcLuhqwhAqRvb3PDUH2nzoOKsY0n_7UUH7_oLAM54CdPFZ8qr9InqRLjgbMJm_wbB_WnZggVfI1pWJDKxSCYPBcVGEHRuwhuh1fDW2qh2E7VpzhuS_lcHc-w' },
  { type: 'pdf', title: 'Match Report - Wimbledon.pdf', size: '2.1 MB • Oct 22', subtitle: 'Report' },
  { type: 'image', title: 'Court Positioning.jpg', size: '4.8 MB • Oct 20', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCP_6sXoSi-ywPam9wJnigYfcGj4pddW03Fod9yEA3CNakifcUt9M6OLQF89AcF162idL3WJb4tobFaONP9HBtWvQP_gbL_L9tKXusXVkdua1Hs16kNNg74MFB01Xc5iSY0kymmd_sp_OEpiazvgU7FlzQRMaafCWmoZLdvbLW2DPA7jdcf5dA6yQ8mIUVbUCFpv6aif0UsC0BM7bNSYOR6pEM1kMLjmYSW1CcLDkEHC2SOyHGUIXzp0fm8RMjUaMIl4xQfBTEWlw' },
  { type: 'video', title: 'Clay Court Footwork.mp4', size: '88.5 MB • Oct 18', duration: '12:15', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDJUAfEepPWyC1Fk3hea88BkXmyJW9egs-tFDGeAKcpITr6cwEoS-etJMaEs8tc5P4EVF6J8ChE3FDgy3EFH3LnfUT_q6jZVOF4mlvvQyQocyWM8wrculKKYTM1CPGlBZSGAoFIi69zYi5zLsuB5VJ6rpQAkJanxHeJZs6kw4PCIYlX4Med7sESVOBg-BRkITiCQk22pRRBuErl0g9P-XCN0xq8R1UGbBZFSBkOHIGKxS2PYZLqI9k028c8SPgQr1UeLm6LG7OEJw' },
  { type: 'pdf', title: 'ATP Scouting Report.pdf', size: '1.2 MB • Oct 15', subtitle: 'Scouting' },
  { type: 'image', title: 'Equipment Specs.png', size: '5.3 MB • Oct 12', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAysoWo97DHbvmFnSnTyudnX_UK6NXEIJGPBMzUNo3DGZ9L22cmkcl4caMrMSmOVAGleYdL4oBeJsyAGu458vLaEa_AzR8Z6ozGN7_gSVVg2TBM_zB_ghefk1-9bdt8lbRhWYhRTtN9NYOBf0tEW8UQenH3eTE5WZZzLsqcDiztOXY7c5DuXpIIrGKX_oP09eMESWn58bdqOy4jdbmfuq3J6vk000mmUj--VjIlMS2RTkcr5MNLvKnlglTljy-2GQaW63K9u5GvnQ' },
  { type: 'video', title: 'Stadium Lighting Test.mov', size: '142 MB • Oct 10', duration: '02:10', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAJLAqipymtHJqHTgLTadvudyZuZRMeQyAaIKDH3_eFuIj41Zn_3jL5IIs-MiIk1q6er4x98gPRQbEoiToePG93Nufd-oig2IGSRjYZ2SsbOq8Oj0LKqYlH0qZ3g-1K1JU6Y7a_crHlZ_ywcX1LmXld1o1uXtgD3K-TpmQIhwEnJKeMRZDsnHN2PvEAbcSfWRiyjeZszEqIhcdEu7M0QwZvg_VwvqdLUdcQyNt5eGc7gI6FKBywuYFgKwSr9N29R1YG5ivMOqJIUA' },
]

export const CHAT_SUGGESTIONS = [
  { title: 'Show player performance trends', desc: 'Deep dive into ELO and form factors.' },
  { title: 'Find matches from 2023', desc: 'Search the complete season archive.' },
  { title: 'Analyze this video', desc: 'Upload a clip for technical AI breakdown.' },
]

export const INITIAL_MESSAGES = [
  { role: 'ai', content: "Hello! I'm your tennis analytics assistant. I can help you analyze player trends, review match data, or break down technical video segments. What are we looking at today?" },
  { role: 'user', content: 'Can you show me the performance trends for top-seeded players in the 2023 tournament?' },
  {
    role: 'ai',
    content: "Based on the 2023 Grand Slam data, there's a significant uptick in serve efficiency among the top 5 seeds compared to previous seasons. Here is a breakdown of the key metrics:",
    chart: [
      { name: 'Player A', pct: 82, color: 'bg-primary' },
      { name: 'Player B', pct: 79, color: 'bg-primary-fixed-dim' },
      { name: 'Player C', pct: 75, color: 'bg-primary' },
    ],
    table: [
      { matchup: 'Final: A vs B', score: '6-4, 7-6', aces: 14 },
      { matchup: 'Semi: B vs C', score: '6-2, 6-3', aces: 8 },
    ],
    followUp: "Would you like me to dive deeper into the technical video analysis for Player A's serve mechanics?",
  },
]

export const DATA_PORTAL_FILTERS = {
  players: ['All Players', 'Carlos Alcaraz', 'Novak Djokovic', 'Jannik Sinner'],
  tournaments: ['Wimbledon', 'French Open', 'US Open', 'Australian Open'],
  years: ['2024', '2023', '2022'],
  matchTypes: ['Match Type', 'Finals', 'Semi-Finals', 'Quarter-Finals'],
}

export const DATA_PORTAL_INSIGHTS = [
  { label: 'Total Matches Recorded', value: '14,282', sub: '+12% this month', icon: 'trending_up', color: 'text-primary', borderColor: 'bg-primary' },
  { label: 'Average Aces / Match', value: '8.4', sub: '+2.1 vs previous year', icon: 'trending_up', color: 'text-primary', borderColor: 'bg-primary' },
  { label: 'Data Quality Score', value: '99.2%', sub: 'Fully Verified', icon: 'check_circle', color: 'text-muted-foreground', borderColor: 'bg-te-outline-variant' },
]
