import { Injectable } from '@angular/core';
import { Product, LumberProduct, SheetGoodProduct } from '../models/product.model';
import { ProductGroup } from '../models/product-group.model';
import { post } from 'aws-amplify/api';

@Injectable({
  providedIn: 'root'
})
export class ProductService {
  async getProductsByPGID(pgid: string): Promise<ProductGroup> {
    try {
      console.log('Getting product by card:', pgid);
      const { body } = await post({
        apiName: 'tezbuildpublic',
        path: `/products`,
        options: {
          headers: {
            'Content-Type': 'application/json',
          },
          body: {
            "action": "getProductsByPGID",
            "pgid": pgid
          }
        }
      }).response;
      const response = await body.json();

      // Ensure response is an object
      if (typeof response === 'object' && Object.keys(response).length > 0) {
        return this.parseProductGroup(response);
      } else {
        console.error('Invalid response format or empty response:', response);
      }
    } catch (error) {
      console.error('Error invoking API:', error);
    }
    return null;
  }

  async getProductById(id: string): Promise<Product[]> {
    try {
      console.log('Getting product by id:', id);
      const { body } = await post({
        apiName: 'tezbuildpublic',
        path: `/products`,
        options: {
          headers: {
            'Content-Type': 'application/json',
          },
          body: {
            "action": "getProductById",
            "id": id
          }
        }
      }).response;
      const response = await body.json();

      // Ensure response is an array
      if (Array.isArray(response) && response.length > 0) {
        return this.parseProducts(response);
      } else {
        console.error('Invalid response format or empty response:', response);
      }
    } catch (error) {
      console.error('Error invoking API:', error);
    }
  
    return [];
  }

  parseProductGroup(response: any): ProductGroup {
    let products = {};
    for (const key in response['Products']) {
      if (Array.isArray(response['Products'][key]) && response['Products'][key].length > 0) {
        products[key] = this.parseProducts(response['Products'][key]);
      }
    }
    return new ProductGroup(
      response['Id'],
      products
    );
  }

  parseProducts(response: any): Product[] {
    const category = response[0]['Category'].toLowerCase();
        
    if (category === 'lumber') {
      return response.map(item => new LumberProduct(
        item['UniqueId'],
        item['Length'],
        item['Width'],
        item['Thickness'],
        item['Weight'],
        item['FacilityId'],
        item['Prices'],
        item['Grade'],
        item['Profile'],
        item['Precision'],
        item['FingerJoint'],
        item['BDFT'],
        item['Species'],
        item['PriceType'],
        item['Heading'],
        item['Subheading'],
        item['Image'],
        item['Treatment'] ? item['Treatment'] : null,
        item['Inventory']? item['Inventory'] : null,
        item['Description']? item['Description'] : null,
        item['Brand']? item['Brand'] : null,
      ));
    } else if (category === 'sheet_good') {
      return response.map(item => new SheetGoodProduct(
        item['UniqueId'],
        item['Length'],
        item['Width'],
        item['Thickness'],
        item['Weight'],
        item['FacilityId'],
        item['Prices'],
        item['PriceType'],
        item['PanelType'],
        item['Heading'],
        item['Subheading'],
        item['Image'],
        item['Treatment'] ? item['Treatment'] : null,
        item['Inventory'] ? item['Inventory'] : null,
        item['Description'] ? item['Description'] : null,
        item['Brand'] ? item['Brand'] : null,
        item['Grade'] ? item['Grade'] : null,
        item['Species'] ? item['Species'] : null,
        item['Edge'] ? item['Edge'] : null,
        item['Finish'] ? item['Finish'] : null,
        item['Origin'] ? item['Origin'] : null,
        item['Metric'] ? item['Metric'] : null,
      ));
    }
    console.error('Unknown product category:', response[0]['Category']);
    return [];
  }
}
