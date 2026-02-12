public with sharing class ClairSentinel implements Schedulable {
    
    // Configurable Thresholds
    private static final Decimal MARKET_RATE_TODAY = 6.125; // This would ideally come from a Custom Setting
    private static final Decimal REFI_BENEFIT_THRESHOLD = 0.75;

    public void execute(SchedulableContext SC) {
        auditPortfolio();
    }

    @future
    public static void auditPortfolio() {
        // 1. Identify "In the Money" candidates
        List<Contact> watchlist = [
            SELECT Id, FirstName, LastName, Current_Rate__c 
            FROM Contact 
            WHERE Current_Rate__c != NULL 
            AND Refi_Ready__c = FALSE
        ];
        
        List<Contact> actionableLeads = new List<Contact>();

        for (Contact c : watchlist) {
            if (isRefiReady(c.Current_Rate__c)) {
                c.Refi_Ready__c = TRUE;
                actionableLeads.add(c);
            }
        }

        // 2. Update the "Live Sheet"
        if (!actionableLeads.isEmpty()) {
            update actionableLeads;
            // Optional: Trigger Jason for immediate outreach
            // JasonOrchestrator.handOffToSwarm(actionableLeads); 
        }
    }

    private static Boolean isRefiReady(Decimal clientRate) {
        return (clientRate - MARKET_RATE_TODAY) >= REFI_BENEFIT_THRESHOLD;
    }
}
