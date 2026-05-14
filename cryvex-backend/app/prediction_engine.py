class LeadPredictor:
    def __init__(self):
        # Base page weight multipliers (Wp)
        self.page_weights = {
            "Home": 1.0,
            "About": 1.0,
            "Blog": 1.0,
            "Textile": 2.0,
            "Manufacturing": 2.0,
            "E-commerce": 2.0
        }

        # Flat action bonuses
        self.action_bonuses = {
            "viewed_strategy": 20,
            "calculated_roi": 15,
            "click": 30  # General CTA click
        }

    def predict(self, current_pulse: dict, historical_stats: dict) -> dict:
        """
        Calculates lead score using strictly linear and additive scoring.
        """
        freq_map = historical_stats.get("freq_map", {})
        section_freq_map = historical_stats.get("section_freq_map", {})
        actions_taken = historical_stats.get("actions_taken", [])
        
        # 1. Dwell Based Points (Anti-Idle/AFK Protection)
        total_dwell_points = 0.0
        max_pulses_per_section = 40  # Cap at 40 pulses per section to prevent AFK inflation
        
        for section, time_steps in section_freq_map.items():
            try:
                t = int(float(time_steps))
            except (ValueError, TypeError):
                t = 0
            # Apply anti-idle cap
            effective_time = min(t, max_pulses_per_section)
            total_dwell_points += (effective_time * 0.5)

        # Apply page multiplier
        current_page = current_pulse.get("current_page", "Home")
        total_dwell_points *= self.page_weights.get(current_page, 1.0)

        # 2. Action Based Points (Cumulative from permanent action record)
        action_points = 0
        for action in actions_taken:
            action_points += self.action_bonuses.get(action, 0)

        # 3. Compile Raw Score
        raw_score = int(total_dwell_points + action_points)
        
        # 4. Enforce Cap
        final_score = min(100, raw_score)

        # 5. Dynamic Messaging / Frontend Hints
        frontend_hint = None
        if "viewed_strategy" in actions_taken and "calculated_roi" not in actions_taken:
            frontend_hint = "User interested in strategy but hasn't run numbers."
        elif raw_score >= 80:
            frontend_hint = "High Intent Engaged Prospect"

        # 6. Find Most Time Spent
        most_time_spent_page = "Unknown"
        if freq_map:
            most_time_spent_page = max(freq_map.items(), key=lambda x: int(float(x[1])) if str(x[1]).replace('.','',1).isdigit() else 0)[0]
            
        most_time_spent_section = "Unknown"
        if section_freq_map:
            most_time_spent_section = max(section_freq_map.items(), key=lambda x: int(float(x[1])) if str(x[1]).replace('.','',1).isdigit() else 0)[0]
            
        # 7. Engagement Persona & Conversion Readiness
        tier = 3 if final_score >= 86 else (2 if final_score >= 61 else (1 if final_score >= 31 else 0))
        personas = {0: "Casual Browser", 1: "Explorer", 2: "Interested Prospect", 3: "Hot Lead"}
        engagement_persona = personas[tier]
        conversion_readiness = round(final_score / 100.0, 2)

        # 8. Page Journey (ordered list of pages visited)
        page_journey = list(freq_map.keys()) if freq_map else [current_page]

        # 9. Dominant Interest (industry vertical with highest dwell)
        industry_pages = {"Textile", "Manufacturing", "E-commerce", "Ecommerce"}
        industry_dwell = {}
        for pg, dw in freq_map.items():
            if pg in industry_pages:
                try:
                    industry_dwell[pg] = int(float(dw))
                except (ValueError, TypeError):
                    industry_dwell[pg] = 0
        dominant_interest = max(industry_dwell, key=industry_dwell.get) if industry_dwell else current_page

        # 10. Actions Summary
        actions_summary = {
            "total_actions": len(actions_taken),
            "has_viewed_strategy": "viewed_strategy" in actions_taken,
            "has_calculated_roi": "calculated_roi" in actions_taken,
            "has_clicked_cta": "cta_clicked" in actions_taken or "click" in actions_taken,
            "has_requested_demo": "demo_requested" in actions_taken,
        }

        return {
            "lead_score": final_score,
            "most_time_spent_page": most_time_spent_page,
            "most_time_spent_section": most_time_spent_section,
            "frontend_hint": frontend_hint,
            "engagement_persona": engagement_persona,
            "conversion_readiness": conversion_readiness,
            "page_journey": page_journey,
            "dominant_interest": dominant_interest,
            "actions_summary": actions_summary,
            "tier": tier,
        }
