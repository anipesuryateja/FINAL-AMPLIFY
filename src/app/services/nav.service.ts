import { Injectable } from '@angular/core';
import { post } from 'aws-amplify/api';
import { PageCard } from '../models/page-card.model';

@Injectable({
  providedIn: 'root'
})
export class NavService {
    private filterValueDictionary: {
        "all": {}
    };

    async getFilterValues(category: string): Promise<any> {
        if (this.filterValueDictionary[category]) {
            return this.filterValueDictionary[category];
        }

        try {
            console.log('Fetching filters:', category);
            const { body } = await post({
                apiName: 'tezbuildpublic',
                path: `/nav`,
                options: {
                headers: {
                    'Content-Type': 'application/json',
                },
                body: {
                    action: "getFilterValues",
                    category
                }
                }
            }).response;
            const response = await body.json();
        
            // Ensure response is an object
            if (typeof response === 'object') {
                this.filterValueDictionary[category] = response;
                return response;
            } else {
                console.error('Invalid response format or empty response:', response);
            }
        } catch (error) {
            console.error('Error invoking API:', error);
        }
        return null;
    }

    async getCardsById(id: string): Promise<any> {
        try {
            console.log('Getting nav page:', id);
            const { body } = await post({
            apiName: 'tezbuildpublic',
            path: `/nav`,
            options: {
                headers: {
                    'Content-Type': 'application/json',
                },
                body: {
                    "action": "getPageCardsByNavID",
                    id
                }
            }
            }).response;
            const response = await body.json();
    
            // Ensure response is an object
            if (typeof response === 'object') {
                const res = {};
                res['cards'] = response['cards'].map((card: any) => {
                    return new PageCard(card.id, card.heading, card.type, card.subheading, card.image);
                });
                res['title'] = response['title'];
                res['filters'] = response['filters'];
                return res;
            } else {
                console.error('Invalid response format or empty response:', response);
            }
        } catch (error) {
            console.error('Error invoking API:', error);
        }
        return null;
    }
}