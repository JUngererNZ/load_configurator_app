# Add to imports
from rules_validator import SARoadTrafficValidator, quick_legal_check

# In your run_optimizer method, add:
def run_optimizer(self):
    # ... existing optimization code ...
    
    # After optimization, run legal audit
    validator = SARoadTrafficValidator(province="WesternCape")  # Change as needed
    audit = validator.full_legal_audit(
        trailer=optimized_trailer,
        items=optimized_trailer.items,
        route=self.route_entry.get() if hasattr(self, 'route_entry') else None
    )
    
    # Display results
    validator.print_legal_report(audit)
    
    if not audit["compliant"]:
        messagebox.showwarning(
            "Legal Compliance Alert",
            "This configuration has legal violations!\n\n"
            "DO NOT DEPART until:\n"
            f"- {len(audit['critical_violations'])} critical violations resolved\n"
            f"- {len(audit['permits_required'])} permits obtained\n\n"
            "See console for full report."
        )