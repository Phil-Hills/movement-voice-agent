import { LightningElement, api, wire } from 'lwc';
import { getRecord, getFieldValue } from 'lightning/uiRecordApi';

const FIELDS = ['Lead.Status', 'Lead.Phone'];

export default class JasonStatus extends LightningElement {
    @api recordId;
    agentStatus = 'Thinking...';
    lastActionDescription = 'Initializing Swarm connection...';

    @wire(getRecord, { recordId: '$recordId', fields: FIELDS })
    lead;

    connectedCallback() {
        // In a real implementation, this would poll the Agent Engine API
        // For MVP, we simulate the status based on Lead Status
        setTimeout(() => {
            this.agentStatus = 'Active Monitoring';
            this.lastActionDescription = 'Jason is monitoring this lead for engagement signals.';
        }, 1500);
    }

    handleViewTranscript() {
        // Placeholder for future feature
        alert('Transcript view coming in v5.3');
    }

    handleForceHandoff() {
        this.agentStatus = 'Handoff Requested';
        this.lastActionDescription = 'Notification sent to LO.';
    }
}
