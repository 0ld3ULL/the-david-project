# Claude Session Brief
*Generated: 2026-02-14 23:09*
*Memories: 2 total — 2 clear, 0 fuzzy, 0 fading*
*Last decay: 2026-02-14T23:00:42.352763*
*Last reconciliation: never*

## Decisions

### AIPulse v2 Path-Based Homepage and Marketplace *****
Built AIPulse v2 with path-based user journeys and marketplace. Phase 1: PathSelector.tsx with 4 paths (Casual, Business, Vibe Coder, Programmer), pathContext.tsx for state, CategoryLeaderCard.tsx (Top 3 + 2 Rising). Phase 2: marketplace_orders/vendor_payouts/seller_stripe_accounts tables, Stripe Connect with 5pct fee via application_fee_amount, marketplace.ts routes. Phase 3: Buy Now in ProductDetail.tsx, MyPurchases.tsx, SellerDashboard.tsx with Stripe Connect onboarding. Also completed Influencer system (InfluencerApply.tsx, InfluencerDashboard.tsx). Plan at peaceful-exploring-swing.md.

### David Score Engine Built for AIPulse *****
Claude J built the David Score engine for AIPulse. 5 indicators: Benchmarks 35pct, Customer Sentiment 30pct, Influencer Sentiment 20pct, Dev Activity 15pct. Database schema in shared/schema.ts with 6 new tables (davidScores, scoreHistory, benchmarkData, sentimentData, devActivityData, aiIntegrationIndex). Scoring engine at server/david_score/engine.ts. TypeScript scrapers adapted from TDP Python scrapers: reddit.ts, github.ts, youtube.ts in server/david_score/scrapers/. API endpoints for scores and admin scraping. UI displays score on ToolCard.tsx and ProductDetail.tsx. CMC-style Apply page built at client/src/pages/Apply.tsx.

---
## Quick Reference

*For full project history, see Memory.md*
*For task list, see tasks/todo.md*
*For lessons learned, see tasks/lessons.md*

### Memory Commands
```
python -m claude_memory brief        # Regenerate this file
python -m claude_memory status       # Memory stats
python -m claude_memory add          # Add a memory interactively
python -m claude_memory decay        # Apply decay manually
python -m claude_memory reconcile    # Git vs memory check
```