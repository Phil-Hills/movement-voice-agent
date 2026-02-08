public with sharing class ClairvoyantCallout {
    private static final String ENDPOINT = 'https://movement-voice-agent-235894147478.us-central1.run.app';

    @AuraEnabled
    public static String chatWithAgent(String text, String thinkingLevel) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(ENDPOINT + '/demo');
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setBody(JSON.serialize(new Map<String, Object>{
            'text' => text,
            'thinking_level' => thinkingLevel,
            'session_id' => 'sf_' + UserInfo.getUserId()
        }));
        return new Http().send(req).getBody();
    }
    
    @AuraEnabled
    public static String getResearch(String company) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(ENDPOINT + '/api/research');
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setBody(JSON.serialize(new Map<String, Object>{'company' => company}));
        return new Http().send(req).getBody();
    }
}
