public with sharing class JasonOrchestrator {
    
    // The Cloud Run Endpoint for the Swarm
    private static final String SWARM_ENDPOINT = 'https://movement-voice-agent.run.app/api/v1/webhook/lead';

    @future(callout=true)
    public static void handOffToSwarm(List<Id> leadIds) {
        List<Lead> leads = [SELECT Id, FirstName, LastName, Phone, Email, Status FROM Lead WHERE Id IN :leadIds];
        
        for (Lead l : leads) {
            try {
                processSingleLead(l);
            } catch (Exception e) {
                System.debug('Error handing off lead ' + l.Id + ': ' + e.getMessage());
            }
        }
    }

    private static void processSingleLead(Lead l) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(SWARM_ENDPOINT);
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setHeader('X-Salesforce-Signature', 'A2AC-SIGNED'); // Placeholder for actual signature
        
        // Payload aligned with Agent Engine schema
        Map<String, Object> payload = new Map<String, Object>{
            'crm_id' => l.Id,
            'first_name' => l.FirstName,
            'last_name' => l.LastName,
            'phone' => l.Phone,
            'email' => l.Email,
            'source' => 'Salesforce MORE'
        };
        
        req.setBody(JSON.serialize(payload));
        
        Http http = new Http();
        HttpResponse res = http.send(req);
        
        if (res.getStatusCode() != 200) {
            System.debug('Swarm rejected handoff: ' + res.getBody());
        }
    }
}
