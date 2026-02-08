import { LightningElement, api, wire, track } from 'lwc';
import { getRecord, getFieldValue } from 'lightning/uiRecordApi';
import LEAD_COMPANY from '@salesforce/schema/Lead.Company';
import chatWithAgent from '@salesforce/apex/ClairvoyantCallout.chatWithAgent';
import getResearch from '@salesforce/apex/ClairvoyantCallout.getResearch';

export default class ClairvoyantAgent extends LightningElement {
    @api recordId;
    @track messages = [];
    @track input = '';
    @track research = null;

    @wire(getRecord, { recordId: '$recordId', fields: [LEAD_COMPANY] })
    lead;

    async handleSend() {
        if (!this.input) return;
        this.messages.push({id: Date.now(), text: this.input, sender: 'user', class: 'outbound'});
        const txt = this.input;
        this.input = '';
        
        try {
            const res = await chatWithAgent({text: txt, thinkingLevel: 'medium'});
            const data = JSON.parse(res);
            this.messages.push({id: Date.now()+1, text: data.text, sender: 'bot', class: 'inbound'});
        } catch (e) {
            this.messages.push({id: Date.now()+1, text: 'Error: '+e.body.message, sender: 'bot', class: 'error'});
        }
    }

    async handleResearch() {
        const company = getFieldValue(this.lead.data, LEAD_COMPANY);
        if (!company) return;
        const res = await getResearch({company});
        this.research = JSON.parse(res);
    }
}
