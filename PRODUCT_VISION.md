# Product vision

Gravel Manager’s mission is to give endurance athletes one trustworthy, athlete-controlled system for training load, planning, health context and race preparation. It turns fragmented records into explainable decisions without locking the product to one provider.

## Users and product surfaces

- The athlete portal is the implemented core: profile, training history, Performance Manager, goals, competitions and manual data imports.
- A coach portal will support consent-based multi-athlete review and recommendations; coach assignment is not implemented in 0.3.0.
- A team portal will add roles, shared standards and oversight on the tenant foundation; invitations, billing and team administration remain out of scope.

The Performance Manager already calculates deterministic CTL, ATL, TSB, rolling load and ramp rate. The Goal Management System now establishes seasons, hierarchical goals and A/B/C competitions. The future Digital Twin will combine longitudinal training and wellness signals into an athlete-specific, inspectable model. AI WorldTour Coach will use that model to suggest—not silently impose—planning decisions, showing evidence, uncertainty and alternatives.

## Trust and commercial direction

Athletes remain authoritative over connections and data. Privacy by design means minimum collection, tenant isolation, encrypted secrets, auditable processing, export/deletion lifecycles and no sensitive logs. AI outputs must be explainable and clearly distinguished from measured facts.

The planned v1.0 scope is a dependable athlete portal with performance analytics, goals/competitions, one production-grade activity-provider integration, robust manual import and transparent recommendation foundations. Coach/team workflows, billing and broader providers can grow this into a commercial multi-tenant SaaS after consent, support and operational controls mature.

Long-term principles are AI-first but human-controlled, provider-independent, one authoritative source per data point, mobile-first, modular, auditable, privacy-preserving and honest about capability. Version 0.3.0 implements the integration foundation; Garmin, TrainingPeaks and CORE remain explicitly non-live placeholders.
