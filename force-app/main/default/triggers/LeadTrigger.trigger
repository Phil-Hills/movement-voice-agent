trigger LeadTrigger on Lead (after insert) {
    // Only fire for new leads that are not yet processed
    List<Id> leadIds = new List<Id>();
    
    for (Lead l : Trigger.new) {
        if (l.Status == 'Open - Not Contacted' && l.Phone != null) {
            leadIds.add(l.Id);
        }
    }
    
    if (!leadIds.isEmpty()) {
        // Hand off to Jason asynchronously
        JasonOrchestrator.handOffToSwarm(leadIds);
    }
}
