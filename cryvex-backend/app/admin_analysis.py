from datetime import datetime, timezone

class AuditEngine:
    def __init__(self):
        # Hardcoded Industry Benchmarks
        self.benchmarks = {
            "Textile": 5.4,
            "Manufacturing": 3.8,
            "Real Estate": 2.1,
            "SaaS": 6.5,
            "E-commerce": 4.2,
            "General": 3.0
        }

    async def generate_audit(self, db, visitor_id: str):
        # Fetch collections
        if type(db).__name__ == 'MockDB':
            all_rois = list(db.roi_calculations.docs.values())
            all_visitors = list(db.visitors.docs.values())
            all_strats = list(db.strategy_prediction.docs.values())
        else:
            try:
                all_rois = await db.roi_calculations.find({}).to_list(length=10000)
                all_visitors = await db.visitors.find({}).to_list(length=10000)
                all_strats = await db.strategy_prediction.find({}).to_list(length=10000)
            except Exception:
                all_rois = []
                all_visitors = []
                all_strats = []

        total_visitors = max(len(all_visitors), 1) # prevent div by zero
        total_roi_users = len(all_rois)
        total_strat_users = len(all_strats)

        # Cryvex Platform Conversion Rate
        cryvex_cvr = round(((total_roi_users + total_strat_users) / total_visitors) * 100, 2)

        # -------- UNNOTICED INSIGHTS GENERATION --------
        insights = []
        
        # 1. Most frequent problem
        problem_counts = {}
        for s in all_strats:
            p = s.get("problem_statement", "General Strategy")
            if len(p) > 5:
                # Basic categorization to clump similar problems
                if "lead" in p.lower() or "traffic" in p.lower() or "growth" in p.lower(): cat = "Lead Generation & Traffic Growth"
                elif "cost" in p.lower() or "spend" in p.lower() or "budget" in p.lower(): cat = "High Ad Spend / Marketing Costs"
                elif "convert" in p.lower() or "sales" in p.lower() or "close" in p.lower(): cat = "Low Conversion Rates & Sales Drops"
                else: cat = "General Operations & Scaling"
                problem_counts[cat] = problem_counts.get(cat, 0) + 1
        
        if problem_counts:
            top_problem = max(problem_counts, key=problem_counts.get)
            insights.append(f"🔍 Top Friction Point: The majority of your users use the Strategy AI to solve '{top_problem}'. You should position your landing pages to directly pitch solutions for this obstacle.")
        else:
            insights.append("🔍 Growth Opportunity: Not enough Strategy AI data. Promote the Business Strategy Module to discover what problems your market struggles with the most.")

        # 2. Most dominant industry
        industry_counts = {}
        for r in all_rois:
            ind = r.get("business_industry", "Unknown")
            if ind != "Unknown" and ind != "General":
                industry_counts[ind] = industry_counts.get(ind, 0) + 1
                
        if industry_counts:
            top_industry = max(industry_counts, key=industry_counts.get)
            insights.append(f"🏢 Primary Vertical: The '{top_industry}' industry shows the highest intent and interacts with the ROI Engine the most. Consider launching dedicated Ad campaigns targeting {top_industry} founders.")
        else:
            insights.append("🏢 Primary Vertical: Your visitors' industries are evenly spread. The system needs more ROI interactions to isolate a clear target market.")

        # 3. Time-of-day behavioral pattern
        hours_active = {}
        for v in all_visitors:
            fv = v.get("first_visit")
            if fv:
                try:
                    # Parses basic ISO to extract hour
                    dt = datetime.fromisoformat(fv.replace("Z", "+00:00"))
                    hr = dt.hour
                    hours_active[hr] = hours_active.get(hr, 0) + 1
                except: pass

        if hours_active:
            top_hr = max(hours_active, key=hours_active.get)
            time_label = "Morning (6AM - 12PM)" if 6 <= top_hr < 12 else "Afternoon (12PM - 5PM)" if 12 <= top_hr < 17 else "Evening (5PM - 10PM)" if 17 <= top_hr < 22 else "Night Owl (10PM - 6AM)"
            insights.append(f"⏰ Peak Attention: Your platform sees heavy engagement during the {time_label}. Schedule email blasts and fresh content drops specifically during these hours for maximum open rates.")

        # -------- PACKAGE INTERACTIVE USER LISTS --------
        formatted_rois = []
        for r in reversed(all_rois):  # Newest first
            inpt = r.get("input_datas", {})
            h_cost = float(inpt.get("manual_hours", 0)) * float(inpt.get("hourly_rate", 0))
            a_cost = 4900 if h_cost < 20000 else (14900 if h_cost < 75000 else 39900)
            
            calc = r.get("calculated_ROI", {})
            net_ben = 0
            if "realistic" in calc:
                net_ben = float(calc["realistic"].get("net_profit", 0))
            elif "conservative" in calc:
                net_ben = float(calc["conservative"].get("net_profit", 0))
                 
            formatted_rois.append({
                "visitor_id": str(r.get("visitor_id")),
                "email": r.get("email", "Not provided"),
                "business_name": r.get("business_name", "Unknown"),
                "industry": r.get("business_industry", "Unknown"),
                "traffic": float(inpt.get("traffic", 0)),
                "cvr": float(inpt.get("conv_rate", 0)),
                "lead_value": float(inpt.get("lead_value", 0)),
                "manual_hours": float(inpt.get("manual_hours", 0)),
                "hourly_rate": float(inpt.get("hourly_rate", 0)),
                "human_cost": h_cost,
                "ai_cost": a_cost,
                "net_benefit": net_ben
            })

        formatted_strats = []
        for s in reversed(all_strats):
            formatted_strats.append({
                "visitor_id": str(s.get("visitor_id")),
                "email": s.get("email", "Not provided"),
                "business_name": s.get("business_name", "Unknown"),
                "business_type": s.get("business_type", "Unknown"),
                "problem": s.get("problem_statement", "Unknown"),
                "strategy_full": str(s.get("generated_strategy", "No Data"))
            })

        formatted_visitors = []
        for v in reversed(all_visitors):
            formatted_visitors.append({
                "visitor_id": str(v.get("visitor_id")),
                "first_visit": str(v.get("first_visit", "Unknown")),
                "last_visited": str(v.get("last_visited", "Unknown")),
                "persona": str(v.get("persona", "Unknown")),
                "score": int(v.get("lead_prediction_score", 0)),
                "category": str(v.get("category", "Unknown")),
                "long_section": str(v.get("long_time_visited_section", "Unknown")),
                "status": str(v.get("status", "Unknown")),
                "page_views": v.get("history", {}) if isinstance(v.get("history", {}), dict) else {},
                "section_views": v.get("section_history", {}) if isinstance(v.get("section_history", {}), dict) else {}
            })

        return {
            "status": "success",
            "global_stats": {
                "total_visitors": total_visitors if not (total_visitors == 1 and len(all_visitors) == 0) else 0,
                "total_roi_users": total_roi_users,
                "total_strat_users": total_strat_users,
                "cryvex_cvr": cryvex_cvr if len(all_visitors) > 0 else 0
            },
            "unnoticed_insights": insights,
            "roi_users": formatted_rois,
            "strategy_users": formatted_strats,
            "all_visitors": formatted_visitors
        }

audit_engine = AuditEngine()
