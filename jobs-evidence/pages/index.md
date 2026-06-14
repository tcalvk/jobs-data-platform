---
title: Jobs Data Platform
---

<style>
  .hero {
    padding: 3.5rem 2.25rem;
    border-radius: 1.5rem;
    background:
      radial-gradient(circle at top left, rgba(59, 130, 246, 0.20), transparent 32%),
      linear-gradient(135deg, #0f172a 0%, #1e293b 52%, #111827 100%);
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.22);
  }

  .eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0.75rem;
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.08);
    color: #dbeafe;
    font-size: 0.85rem;
    font-weight: 650;
    letter-spacing: 0.02em;
    margin-bottom: 1.25rem;
  }

  .hero h1 {
    max-width: 980px;
    font-size: clamp(2.4rem, 6vw, 5.2rem);
    line-height: 0.95;
    letter-spacing: -0.07em;
    margin: 0 0 1.25rem 0;
    color: white;
  }

  .hero p {
    max-width: 760px;
    font-size: 1.15rem;
    line-height: 1.7;
    color: #cbd5e1;
    margin-bottom: 1.75rem;
  }

  .hero-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.9rem;
    margin-top: 1.5rem;
  }

  .button-primary,
  .button-secondary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.8rem 1.1rem;
    border-radius: 0.8rem;
    font-weight: 750;
    text-decoration: none !important;
  }

  .button-primary {
    background: white;
    color: #0f172a !important;
  }

  .button-secondary {
    color: white !important;
    border: 1px solid rgba(255, 255, 255, 0.28);
    background: rgba(255, 255, 255, 0.08);
  }

  .section-kicker {
    color: #2563eb;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.8rem;
    margin-bottom: 0.4rem;
  }

  .section-heading {
    font-size: 2rem;
    letter-spacing: -0.04em;
    margin: 0 0 0.75rem 0;
  }

  .section-copy {
    max-width: 820px;
    color: #475569;
    font-size: 1.05rem;
    line-height: 1.65;
    margin-bottom: 1.5rem;
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
    margin: 1.5rem 0 2.5rem 0;
  }

  .dashboard-card {
    position: relative;
    overflow: hidden;
    border: 1px solid #e2e8f0;
    border-radius: 1.25rem;
    padding: 1.35rem;
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
    min-height: 330px;
  }

  .dashboard-card:before {
    content: "";
    position: absolute;
    inset: 0;
    height: 5px;
    background: linear-gradient(90deg, #2563eb, #14b8a6, #f59e0b);
  }

  .card-icon {
    width: 2.7rem;
    height: 2.7rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.9rem;
    background: #eff6ff;
    font-size: 1.4rem;
    margin-bottom: 1rem;
  }

  .dashboard-card h3 {
    font-size: 1.35rem;
    letter-spacing: -0.03em;
    margin: 0 0 0.35rem 0;
  }

  .question {
    font-size: 1.05rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0.35rem 0 1rem 0;
  }

  .dashboard-card p {
    color: #475569;
    line-height: 1.6;
    margin-bottom: 1rem;
  }

  .card-list {
    padding-left: 1.1rem;
    color: #475569;
    line-height: 1.55;
    margin-bottom: 1.2rem;
  }

  .card-link {
    position: absolute;
    left: 1.35rem;
    bottom: 1.25rem;
    font-weight: 800;
    text-decoration: none !important;
    color: #2563eb !important;
  }

  .feature-strip {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.9rem;
    margin: 1.5rem 0 2.75rem 0;
  }

  .feature {
    border: 1px solid #e2e8f0;
    border-radius: 1rem;
    padding: 1rem;
    background: #ffffff;
  }

  .feature strong {
    display: block;
    color: #0f172a;
    margin-bottom: 0.25rem;
  }

  .feature span {
    color: #64748b;
    font-size: 0.95rem;
    line-height: 1.45;
  }

  .workflow {
    border-radius: 1.25rem;
    border: 1px solid #e2e8f0;
    background: #f8fafc;
    padding: 1.35rem;
    margin: 1.5rem 0 2.75rem 0;
  }

  .workflow-steps {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.75rem;
  }

  .step {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 1rem;
    padding: 1rem;
  }

  .step-number {
    font-size: 0.8rem;
    color: #2563eb;
    font-weight: 850;
    margin-bottom: 0.35rem;
  }

  .step strong {
    display: block;
    margin-bottom: 0.25rem;
  }

  .step span {
    color: #64748b;
    font-size: 0.92rem;
    line-height: 1.4;
  }

  .callout {
    border-left: 5px solid #2563eb;
    background: #eff6ff;
    border-radius: 1rem;
    padding: 1.2rem 1.35rem;
    margin: 1.5rem 0 2.5rem 0;
  }

  .callout p {
    margin: 0;
    color: #1e3a8a;
    line-height: 1.65;
  }

  @media (max-width: 900px) {
    .dashboard-grid,
    .feature-strip,
    .workflow-steps {
      grid-template-columns: 1fr;
    }

    .dashboard-card {
      min-height: auto;
      padding-bottom: 4rem;
    }
  }
</style>

<div class="hero">
  <div class="eyebrow">Labor-market intelligence for data careers</div>

  <h1>Turn job postings into career strategy.</h1>

  <p>
    The Jobs Data Platform analyzes real job listings to surface demand, compensation, skill requirements, and market movement across selected roles and locations. It is designed to help job seekers decide where to focus, what to learn, and how the market is changing.
  </p>

  <div class="hero-actions">
    <a class="button-primary" href="/career-opportunity-explorer">Explore Opportunities</a>
    <a class="button-secondary" href="#dashboards">View Reports</a>
  </div>
</div>

<div class="section-kicker">Platform purpose</div>
<h2 class="section-heading">A decision layer on top of job market data</h2>

<p class="section-copy">
  Most job searches start with scattered listings, broad salary guesses, and anecdotal advice. This platform restructures that noisy data into a set of focused reports that answer practical career questions: which roles look strongest, which skills show up most often, and whether the market is expanding or cooling.
</p>

<div class="feature-strip">
  <div class="feature">
    <strong>Role demand</strong>
    <span>Compare hiring activity across titles, locations, and time periods.</span>
  </div>

  <div class="feature">
    <strong>Skill signals</strong>
    <span>Identify the tools, technologies, and capabilities employers request.</span>
  </div>

  <div class="feature">
    <strong>Salary context</strong>
    <span>Use parsed pay ranges to understand compensation bands by role.</span>
  </div>

  <div class="feature">
    <strong>Market movement</strong>
    <span>Track active, new, and removed postings to understand trend direction.</span>
  </div>
</div>

<div id="dashboards" class="section-kicker">Reports</div>
<h2 class="section-heading">Choose the question you want to answer</h2>

<p class="section-copy">
  Each report is organized around a decision. Start with the question that best matches what you are trying to figure out.
</p>

<div class="dashboard-grid">
  <div class="dashboard-card">
    <div class="card-icon">🎯</div>
    <h3>Career Opportunity Explorer</h3>
    <div class="question">Which role should I target right now?</div>
    <p>
      Compare roles using opportunity-oriented signals such as active demand, growth, salary strength, and role-level patterns.
    </p>
    <ul class="card-list">
      <li>Role comparison</li>
      <li>Opportunity score ranking</li>
      <li>Demand and salary context</li>
      <li>Location and seniority filters</li>
    </ul>
    <a class="card-link" href="/career-opportunity-explorer">Open report →</a>
  </div>

  <div class="dashboard-card">
    <div class="card-icon">🧠</div>
    <h3>Skills Intelligence</h3>
    <div class="question">Which skills should I learn or prioritize?</div>
    <p>
      Explore skill demand across postings to understand which capabilities are broadly valuable, role-specific, or rising in importance.
    </p>
    <ul class="card-list">
      <li>Top requested skills</li>
      <li>Skill demand by role</li>
      <li>Skill clusters and patterns</li>
      <li>Learning prioritization signals</li>
    </ul>
    <a class="card-link" href="/skills-intelligence">Open report →</a>
  </div>

  <div class="dashboard-card">
    <div class="card-icon">📈</div>
    <h3>Market Dynamics</h3>
    <div class="question">What is happening in the job market over time?</div>
    <p>
      Monitor how the market changes through new postings, active listings, removed listings, salary movement, and platform mix.
    </p>
    <ul class="card-list">
      <li>Job lifecycle trends</li>
      <li>Active vs. removed postings</li>
      <li>Market movement by role</li>
      <li>Posting velocity over time</li>
    </ul>
    <a class="card-link" href="/market-dynamics">Open report →</a>
  </div>
</div>

<div class="section-kicker">Data engineering foundation</div>
<h2 class="section-heading">Built as an end-to-end analytics engineering project</h2>

<p class="section-copy">
  Behind the reports is a cloud data pipeline that ingests job listings, stores raw source data, standardizes fields, deduplicates postings, enriches skills, and publishes reporting-ready models. The project is intentionally scoped to a curated set of roles and locations so the full lifecycle can be demonstrated clearly without unnecessary scale for scale’s sake.
</p>

<div class="workflow"><div class="workflow-steps"><div class="step"><div class="step-number">01</div><strong>Ingest</strong><span>Collect job listings from SerpAPI and LinkedIn.</span></div><div class="step"><div class="step-number">02</div><strong>Store</strong><span>Persist raw responses and structured records in cloud storage and BigQuery.</span></div><div class="step"><div class="step-number">03</div><strong>Model</strong><span>Transform, deduplicate, parse salaries, and derive reporting dimensions.</span></div><div class="step"><div class="step-number">04</div><strong>Enrich</strong><span>Extract skills and convert raw listings into analysis-ready signals.</span></div><div class="step"><div class="step-number">05</div><strong>Publish</strong><span>Serve interactive reports through Evidence.</span></div></div></div>

<div class="callout">
  <p>
    <strong>Current scope:</strong> This is a proof-of-concept focused on a controlled set of job titles and locations. The goal is not to index every job posting on the internet; it is to demonstrate a reliable data product pattern from ingestion through decision-ready analytics.
  </p>
</div>

<div class="section-kicker">Start here</div>
<h2 class="section-heading">Recommended path</h2>

<p class="section-copy">
  Start with <strong>Career Opportunity Explorer</strong> to compare roles, use <strong>Skills Intelligence</strong> to understand what to learn next, and then use <strong>Market Dynamics</strong> to see whether the market is moving in your favor over time.
</p>
