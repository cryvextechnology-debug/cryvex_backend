"""
Cryvex Industry Knowledge Base — Structured facts for Digital Employee personalization.
Provides industry-specific insights for Textile, Manufacturing, and E-commerce verticals.
Each entry has: fact, insight, cryvex_solution, conversion_hook (EN + Tanglish).
"""


class IndustryKnowledge:
    """Selects industry facts based on vertical, section, score tier, and visit rotation."""

    TEXTILE = {
        "section-hero": [
            {"fact": "India's textile sector is the world's 2nd largest — ₹7 lakh crore GDP contribution.",
             "insight": "Yet 35% of that potential leaks through manual inefficiency on factory floors.",
             "cryvex_solution": "Cryvex seals those leaks with AI-driven shop-floor orchestration.",
             "hook": "A free 30-min audit maps exactly where your unit is leaking.",
             "fact_ta": "India textile sector world 2nd largest — ₹7 lakh crore GDP.",
             "insight_ta": "Aana 35% potential manual inefficiency-la factory floor-la leak aagudhu.",
             "solution_ta": "Cryvex AI shop-floor orchestration kooda adha seal pannudhu.",
             "hook_ta": "Free 30-min audit unga unit enga leak aagudhu nu exact-ah map pannum."},
            {"fact": "Tiruppur exports ₹42,000 crore in knitwear annually — India's largest cluster.",
             "insight": "Most units still track inventory on paper and call suppliers by phone.",
             "cryvex_solution": "Our Digital Employee automates supplier coordination and inventory tracking 24/7.",
             "hook": "Your competitor who automated last year now operates at 31% lower cost.",
             "fact_ta": "Tiruppur annually ₹42,000 crore knitwear export — India's largest cluster.",
             "insight_ta": "Aana most units paper-la inventory track, phone-la suppliers call panranga.",
             "solution_ta": "Enga Digital Employee supplier coordination and inventory 24/7 automate pannum.",
             "hook_ta": "Last year automate panna competitor 31% lower cost-la operate panraanga."},
            {"fact": "Manual cutting wastes 22% of fabric on average across Tamil Nadu mills.",
             "insight": "For a unit running 10,000 garments/day, that's ₹4+ lakhs lost every month.",
             "cryvex_solution": "AI precision cutting drops waste below 6% — recovering ₹4 lakhs monthly.",
             "hook": "We've done this for 14 active clients with zero export rejections for 18 months.",
             "fact_ta": "Tamil Nadu mills-la manual cutting average 22% fabric waste panudhu.",
             "insight_ta": "10,000 garments/day unit-ku monthly ₹4+ lakhs loss.",
             "solution_ta": "AI precision cutting waste 6%-ku kudaikum — monthly ₹4 lakhs recover.",
             "hook_ta": "14 clients-ku 18 months zero export rejection — enga track record."},
        ],
        "section-pillars": [
            {"fact": "A 500-loom unit loses ₹3.5–6 lakhs/month to labor dependency, waste, scaling friction, and digital gap.",
             "insight": "These four silent killers compound — and most owners don't measure them separately.",
             "cryvex_solution": "We plug every one with targeted AI modules — measurable from day one.",
             "hook": "Our audit quantifies each leak individually so you see exactly where money goes.",
             "fact_ta": "500-loom unit monthly ₹3.5–6 lakhs labor, waste, scaling, digital gap-la lose panudhu.",
             "insight_ta": "Idha naalay silent killers — most owners separately measure panradhilla.",
             "solution_ta": "Targeted AI modules kooda ovvoru leak-um plug pannuvom — day one measurable.",
             "hook_ta": "Enga audit ovvoru leak-um individually quantify pannum."},
            {"fact": "Computer vision detects fabric defects at 99.8% accuracy at full line speed.",
             "insight": "Manual QA catches at best 93–95%. The 5–7% missed becomes rework and buyer penalties.",
             "cryvex_solution": "Zero additional inspectors needed. Zero production slowdown.",
             "hook": "One client reduced QA costs from ₹14 lakhs to ₹1.8 lakhs per month.",
             "fact_ta": "Computer vision full line speed-la 99.8% accuracy defects detect pannum.",
             "insight_ta": "Manual QA 93–95% mattum catch. 5–7% miss — rework, penalties.",
             "solution_ta": "Extra inspectors vendam. Production slow aagadhu.",
             "hook_ta": "Oru client QA cost ₹14 lakhs-la irundhu ₹1.8 lakhs-ku kudaichu."},
        ],
        "section-roi": [
            {"fact": "Textile units that automate top 3 bottlenecks save ₹8–15 lakhs in their first quarter.",
             "insight": "That's not a projection — it's the average from our existing client base.",
             "cryvex_solution": "Our ROI calculator shows your specific savings potential in 2 minutes.",
             "hook": "Calculate your exact numbers — completely free, no commitment.",
             "fact_ta": "Top 3 bottlenecks automate panna textile units first quarter ₹8–15 lakhs save.",
             "insight_ta": "Projection illa — enga existing client base average.",
             "solution_ta": "ROI calculator 2 minutes-la unga specific savings kaattum.",
             "hook_ta": "Unga exact numbers calculate pannunga — completely free."},
        ],
        "section-cases": [
            {"fact": "Kanchipuram Weavers Guild digitized 347 heritage patterns — now receiving global orders 24/7.",
             "insight": "Zero new employees. ₹2.8 crore additional revenue. A 200-year tradition made globally searchable.",
             "cryvex_solution": "WhatsApp AI handles orders automatically while weavers focus on craftsmanship.",
             "hook": "Your trade circle will notice when your metrics outperform the cluster average.",
             "fact_ta": "Kanchipuram Weavers Guild 347 heritage patterns digitize — global orders 24/7.",
             "insight_ta": "Zero new employees. ₹2.8 crore additional revenue. 200-year tradition globally searchable.",
             "solution_ta": "WhatsApp AI orders handle pannum — weavers craftsmanship-la focus.",
             "hook_ta": "Unga metrics cluster average outperform pannunga — trade circle notice pannum."},
        ],
        "section-cta": [
            {"fact": "Every week without automation costs ₹85,000–₹1.4 lakhs for a mid-scale textile unit.",
             "insight": "Compounded energy waste, labor inefficiency, and quality rejection.",
             "cryvex_solution": "Our 30-minute consultation produces a factory-specific action plan with real numbers.",
             "hook": "Click Consult an Expert — a Cryvex textile specialist reaches you within 24 hours.",
             "fact_ta": "Automation illaamal oru week mid-scale unit-ku ₹85,000–₹1.4 lakhs cost.",
             "insight_ta": "Energy waste, labor inefficiency, quality rejection compound aagudhu.",
             "solution_ta": "30-minute consultation factory-specific action plan with real numbers.",
             "hook_ta": "Consult an Expert click pannunga — 24 hours-la specialist contact panniduvaanga."},
        ],
    }

    MANUFACTURING = {
        "section-hero": [
            {"fact": "India's manufacturing contributes 17% to GDP — yet 60% of SME factories use reactive maintenance.",
             "insight": "Reactive maintenance costs 3–5x more than predictive. Most owners don't measure the gap.",
             "cryvex_solution": "Cryvex AI detects faults 72 hours before breakdown — zero surprise shutdowns.",
             "hook": "A free operational audit reveals your exact downtime cost per month.",
             "fact_ta": "India manufacturing GDP 17% — aana 60% SME factories reactive maintenance use panranga.",
             "insight_ta": "Reactive maintenance predictive-ah vida 3–5x costly. Most owners gap measure panradhilla.",
             "solution_ta": "Cryvex AI 72 hours munnaadi faults detect — zero surprise shutdowns.",
             "hook_ta": "Free operational audit unga exact monthly downtime cost reveal pannum."},
            {"fact": "Chennai is India's Detroit — home to 40% of auto-parts manufacturing.",
             "insight": "Most units experience 3–5 unplanned shutdowns per month at ₹8,000 per idle hour.",
             "cryvex_solution": "Predictive maintenance flags failures before they cascade into ₹2–3 lakhs daily loss.",
             "hook": "One client saw 4.3x ROI in 12 months — ₹12 lakhs invested, ₹52 lakhs returned.",
             "fact_ta": "Chennai India's Detroit — 40% auto-parts manufacturing.",
             "insight_ta": "Most units monthly 3–5 unplanned shutdowns — ₹8,000 per idle hour.",
             "solution_ta": "Predictive maintenance failures cascade aaga munnadi flag pannum.",
             "hook_ta": "Oru client 12 months-la 4.3x ROI — ₹12 lakhs invest, ₹52 lakhs return."},
        ],
        "section-pillars": [
            {"fact": "A mid-scale factory loses ₹18–35 lakhs per year to labor dependency, quality rejection, knowledge silos, and downtime.",
             "insight": "These four bottlenecks compound silently — they don't appear on your P&L but they cap your growth.",
             "cryvex_solution": "We have a specific, deployed AI solution for each one.",
             "hook": "Our audit identifies which bottleneck is bleeding you the most — in under 30 minutes.",
             "fact_ta": "Mid-scale factory annually ₹18–35 lakhs labor, quality, knowledge silos, downtime-la lose.",
             "insight_ta": "Idha naalay silently compound — P&L-la teriyaadhu aana growth cap pannum.",
             "solution_ta": "Ovvoru-ku specific deployed AI solution irukku.",
             "hook_ta": "30 minutes-la which bottleneck most bleed panudhu nu audit identify pannum."},
        ],
        "section-roi": [
            {"fact": "40% increase in operational efficiency — measurable in the first 45 days.",
             "insight": "35% cycle time reduction with near-zero error rates across our manufacturing clients.",
             "cryvex_solution": "Scale output without proportional increase in labor costs.",
             "hook": "Project your specific numbers with our manufacturing ROI calculator.",
             "fact_ta": "First 45 days-la 40% operational efficiency increase — measurable.",
             "insight_ta": "35% cycle time reduction, near-zero error rates — enga manufacturing clients.",
             "solution_ta": "Labor cost proportional increase illaamal output scale pannunga.",
             "hook_ta": "Manufacturing ROI calculator-la unga specific numbers project pannunga."},
        ],
        "section-cases": [
            {"fact": "A legacy steel giant saved ₹2.2 crore annually with real-time furnace monitoring — zero equipment replaced.",
             "insight": "PCB assembly client doubled output in 8 months. Same floor, same machines — AI logic was the only addition.",
             "cryvex_solution": "Neural network optimized supply chain saved ₹4.8 crore in transit delays for an automotive hub.",
             "hook": "Every case study started with one free audit conversation.",
             "fact_ta": "Legacy steel giant real-time furnace monitoring-la annually ₹2.2 crore save — zero equipment replace.",
             "insight_ta": "PCB client 8 months-la output double. Same floor, same machines — AI logic mattum add.",
             "solution_ta": "Automotive hub-ku neural network supply chain optimize — ₹4.8 crore transit delays save.",
             "hook_ta": "Every case study oru free audit conversation-la start aaguchu."},
        ],
        "section-cta": [
            {"fact": "Every week without predictive maintenance costs ₹56,000 on average.",
             "insight": "Energy waste, emergency repairs, and missed delivery penalties — calculated across 47 clients.",
             "cryvex_solution": "A 30-minute consultation produces a factory-specific efficiency roadmap at zero cost.",
             "hook": "Your competitor in the same industrial estate may already be automating.",
             "fact_ta": "Predictive maintenance illaamal oru week average ₹56,000 cost.",
             "insight_ta": "Energy waste, emergency repairs, delivery penalties — 47 clients-la calculate panni.",
             "solution_ta": "30-minute consultation factory-specific efficiency roadmap — zero cost.",
             "hook_ta": "Same industrial estate-la unga competitor already automating iruppaanga."},
        ],
    }

    ECOMMERCE = {
        "section-hero": [
            {"fact": "India's e-commerce market will reach ₹7 lakh crore by 2026.",
             "insight": "But 68% of that revenue is lost to cart abandonment, stockouts, and poor retention.",
             "cryvex_solution": "Cryvex replaces fragmented retail operations with a single AI-driven ecosystem.",
             "hook": "A free audit maps your exact cart recovery potential and churn risk.",
             "fact_ta": "India e-commerce ₹7 lakh crore by 2026 reach aagum.",
             "insight_ta": "Aana 68% revenue cart abandonment, stockouts, poor retention-la lose.",
             "solution_ta": "Cryvex fragmented retail operations-a single AI ecosystem-ah replace pannum.",
             "hook_ta": "Free audit unga cart recovery potential and churn risk map pannum."},
            {"fact": "70% of all shopping carts are abandoned globally.",
             "insight": "For a store doing 1,000 sessions/day, that's 700 potential sales vanishing silently.",
             "cryvex_solution": "Sentiment Shield identifies why each customer left and re-engages them automatically.",
             "hook": "A D2C brand protected ₹64 lakhs/month using our churn detection AI.",
             "fact_ta": "Globally 70% shopping carts abandoned aagudhu.",
             "insight_ta": "1,000 sessions/day store-ku 700 potential sales silently vanish.",
             "solution_ta": "Sentiment Shield each customer ena karanam pogiraanga nu identify panni re-engage pannum.",
             "hook_ta": "D2C brand monthly ₹64 lakhs enga churn detection AI use panni protect panni."},
        ],
        "section-pillars": [
            {"fact": "A single stockout event permanently loses 23% of customers who encountered it.",
             "insight": "Inventory mismatch, churn, delivery failure, cart abandonment account for 40–60% of preventable revenue loss.",
             "cryvex_solution": "Organic Replenishment AI eliminates stockouts entirely — not just reduces them.",
             "hook": "Sentiment Shield detects churn 14 days before a customer leaves.",
             "fact_ta": "Oru stockout event encounter panna 23% customers permanently lose aagudhu.",
             "insight_ta": "Inventory mismatch, churn, delivery, cart abandon — 40–60% preventable revenue loss.",
             "solution_ta": "Organic Replenishment AI stockouts eliminate — reduce pannaadhu, eliminate.",
             "hook_ta": "Sentiment Shield customer leave panna 14 days munnaadi churn detect pannum."},
        ],
        "section-roi": [
            {"fact": "2.4x customer retention, 67% cart recovery rate, 3.8x LTV multiplier — audited client data.",
             "insight": "20–30% revenue silently leaks through every campaign, every abandoned cart, every stockout.",
             "cryvex_solution": "Our AI seals those leaks permanently with behavioral intelligence.",
             "hook": "Project your growth numbers — completely free.",
             "fact_ta": "2.4x retention, 67% cart recovery, 3.8x LTV — audited client data.",
             "insight_ta": "20–30% revenue every campaign, cart, stockout-la silently leak aagudhu.",
             "solution_ta": "Enga AI behavioral intelligence kooda leaks permanently seal pannum.",
             "hook_ta": "Unga growth numbers project pannunga — completely free."},
        ],
        "section-cases": [
            {"fact": "Multi-brand portal saved ₹38 lakhs in 6 months from inventory AI alone.",
             "insight": "Grocery chain improved on-time delivery from 67% to 96% in 90 days — zero new vehicles.",
             "cryvex_solution": "Same vehicles, same staff — just AI intelligence applied to existing infrastructure.",
             "hook": "You could be our next case study in your product category.",
             "fact_ta": "Multi-brand portal inventory AI alone 6 months-la ₹38 lakhs save.",
             "insight_ta": "Grocery chain 90 days-la 67% → 96% on-time delivery — zero new vehicles.",
             "solution_ta": "Same vehicles, same staff — existing infrastructure-ku AI intelligence.",
             "hook_ta": "Unga product category-la next case study neenga aagalaam."},
        ],
        "section-cta": [
            {"fact": "Every week without cart recovery AI costs ₹1.4–2.8 lakhs in a mid-scale store.",
             "insight": "Compounded abandonment loss, preventable churn, and inventory waste.",
             "cryvex_solution": "The audit maps your exact cart recovery potential, churn risk, and inventory gap.",
             "hook": "A Cryvex e-commerce specialist contacts you within 24 hours — zero cost.",
             "fact_ta": "Cart recovery AI illaamal oru week mid-scale store-ku ₹1.4–2.8 lakhs cost.",
             "insight_ta": "Abandonment loss, preventable churn, inventory waste compound aagudhu.",
             "solution_ta": "Audit unga exact cart recovery, churn risk, inventory gap map pannum.",
             "hook_ta": "24 hours-la Cryvex e-commerce specialist contact — zero cost."},
        ],
    }

    # General/Home page knowledge
    GENERAL = {
        "section-hero": [
            {"fact": "Cryvex AI transforms traditional websites into proactive digital employees.",
             "insight": "I'm here to understand your interests and provide helpful guidance while you browse.",
             "cryvex_solution": "We help South Indian manufacturers capture up to 40% more high-value B2B leads.",
             "hook": "Tell us your industry — we'll show you specific savings.",
             "fact_ta": "Cryvex AI traditional websites-a proactive digital employees-ah transform pannum.",
             "insight_ta": "Enga platform unga interests-ah purinjukitu, neenga browse pannum bothey ungaluku help pannum.",
             "solution_ta": "South Indian manufacturers-ku 40% more high-value B2B leads capture panna help pannuvom.",
             "hook_ta": "Unga industry sollunga — specific savings kaattuvom."},
        ],
    }

    VERTICALS = {
        "Textile": TEXTILE,
        "Manufacturing": MANUFACTURING,
        "E-commerce": ECOMMERCE,
        "Ecommerce": ECOMMERCE,
        "Home": GENERAL,
        "About": GENERAL,
        "Blog": GENERAL,
    }

    # Warmth greetings based on journey depth
    WARMTH_EN = {
        0: ["Welcome!", "Hi there!", "Hello!"],
        1: ["Good to see you exploring.", "Thanks for checking us out.", "Glad you're here."],
        2: ["You've been thorough — I respect that.", "I can see you're evaluating seriously.", "Your engagement tells me you recognize the opportunity."],
        3: ["You've explored deeper than 95% of visitors.", "Your level of engagement is exceptional.", "I can tell you're ready for the next step."],
    }
    WARMTH_TA = {
        0: ["Vanakkam!", "Welcome!", "Hello!"],
        1: ["Explore panradhu nalla irukku.", "Check out panradhukku thanks.", "Neenga vandhadhu nalladhu."],
        2: ["Thoroughly evaluate panringa — respect.", "Seriously evaluate panringa nu theriyudhu.", "Opportunity recognize panringa."],
        3: ["95% visitors-ah vida deeper explore panni irukkinga.", "Unga engagement exceptional.", "Next step-ku ready nu theriyudhu."],
    }

    # Conversion hooks per tier
    HOOKS_EN = {
        0: ["Explore our solutions to learn more.", "Keep reading — the insights get deeper.", "Browse at your pace — we're here when you're ready."],
        1: ["We can help you solve this — explore our case studies.", "See how similar businesses transformed.", "Curious? Our ROI calculator shows your potential savings."],
        2: ["Based on your interest, a free strategy audit would give you clarity.", "Let us build your specific roadmap — 30 minutes, zero cost.", "Your industry peers are already seeing results."],
        3: ["Your potential savings: ₹8–15 lakhs per quarter. Let's validate in a free 30-min call.", "Click Consult an Expert — we'll prioritize your session.", "First-mover advantage is worth 18 months of uncatchable lead time. Act now."],
    }
    HOOKS_TA = {
        0: ["Solutions explore pannunga.", "Padichu paarunga — insights innum deeper.", "Unga pace-la browse pannunga."],
        1: ["Similar businesses eppadi transform aaganga nu paarunga.", "ROI calculator unga savings kaattum.", "Case studies check pannunga."],
        2: ["Free strategy audit unga ku clarity kudukkum.", "30 minutes, zero cost — unga roadmap build pannuvom.", "Unga industry peers already results paachirukkanga."],
        3: ["Quarterly ₹8–15 lakhs savings potential. Free 30-min call-la validate pannalama?", "Consult an Expert click pannunga — unga session priority.", "First-mover advantage 18 months worth. Ippo act pannunga."],
    }

    PERSONAS = {0: "Casual Browser", 1: "Explorer", 2: "Interested Prospect", 3: "Hot Lead"}

    @classmethod
    def get_knowledge(cls, vertical: str, section: str, tier: int, visit_count: int = 0) -> dict:
        """Returns a knowledge payload for the given context."""
        vdata = cls.VERTICALS.get(vertical, cls.GENERAL)
        entries = vdata.get(section, vdata.get("section-hero", cls.GENERAL["section-hero"]))
        entry = entries[visit_count % len(entries)]

        t = min(tier, 3)
        v_idx = visit_count % 3

        return {
            "fact": entry["fact"],
            "insight": entry["insight"],
            "cryvex_solution": entry["cryvex_solution"],
            "conversion_hook": entry["hook"],
            "fact_ta": entry.get("fact_ta", entry["fact"]),
            "insight_ta": entry.get("insight_ta", entry["insight"]),
            "solution_ta": entry.get("solution_ta", entry["cryvex_solution"]),
            "hook_ta": entry.get("hook_ta", entry["hook"]),
            "warmth_en": cls.WARMTH_EN[t][v_idx],
            "warmth_ta": cls.WARMTH_TA[t][v_idx],
            "tier_hook_en": cls.HOOKS_EN[t][v_idx],
            "tier_hook_ta": cls.HOOKS_TA[t][v_idx],
            "persona": cls.PERSONAS[t],
        }


# Singleton
industry_kb = IndustryKnowledge()
