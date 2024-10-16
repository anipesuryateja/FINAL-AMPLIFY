import { ProductDictionary } from './product-dictionary.model';
import shajs from 'sha.js';

class Price {
    price: number;
    packSize: number;
    constructor(price: number, packSize: number) {
        this.price = price;
        this.packSize = packSize;
    }
}

export abstract class Product {
    id: string;
    inventory?: number;
    description?: string;
    length: number;
    width: number;
    thickness: number;
    weight: number;
    facilityId: string;
    prices: Price[]; // should always be in increasing order of quantity
    priceType: string; // a for adder, b for breakpoint
    category: string;
    heading: string;
    subheading: string;
    image: string;
    brand?: string; // this field denotes a non-commodity item
    origin?: string;
    metric?: boolean;

    constructor(
        id: string,
        length: number,
        width: number,
        thickness: number,
        weight: number,
        facilityId: string,
        prices: number[][],
        priceType: string,
        heading: string,
        subheading: string,
        image: string,
        inventory?: number,
        description?: string,
        brand?: string,
        origin?: string,
        metric?: boolean
    ) {
        this.id = id;
        this.length = length;
        this.width = width;
        this.thickness = thickness;
        this.weight = Math.round(weight*1000)/1000;
        this.facilityId = facilityId;
        this.prices = prices
            .map(([price, quantity]) => new Price(price, quantity))
            .sort((a, b) => a.packSize - b.packSize); // Sort in ascending order of pack size
        this.priceType = priceType;
        this.inventory = inventory;
        this.description = description;
        this.brand = brand;
        this.origin = origin;
        this.heading = heading;
        this.subheading = subheading;
        this.image = image;
        this.metric = metric? true : false;
    }

    get formattedThickness(): string {
        return Product.formatDistance(this.thickness);
    }

    get formattedLength(): string {
        return Product.formatDistance(this.length);
    }

    get formattedWidth(): string {
        return Product.formatDistance(this.width);
    }

    static formatDistance(distance: number, metric?: boolean): string {
        if (metric) {
          return `${distance}mm`;
        } else {
          const feet = Math.floor(distance / 12);
          const remainingInches = distance % 12;
          const wholeInches = Math.floor(remainingInches);
          const fractionalInches = remainingInches - wholeInches;
          let fraction = '';
    
          if (fractionalInches > 0) {
            const gcd = (a: number, b: number): number => b ? gcd(b, a % b) : a;
            const denominator = 32;
            const numerator = Math.round(fractionalInches * denominator);
            const commonDivisor = gcd(numerator, denominator);
            const simplifiedNumerator = numerator / commonDivisor;
            const simplifiedDenominator = denominator / commonDivisor;
    
            if (simplifiedNumerator > 0) {
              fraction = `${simplifiedNumerator}/${simplifiedDenominator}`;
            }
          }
    
          let result = '';
          if (feet > 0) {
            result += `${feet}ft.`;
          }
    
          let inFlag = false;
          if (wholeInches > 0) {
            inFlag = true;
            if (result !== '') {
              result += ' ';
            }
            result += `${wholeInches}`;
          }
    
          if (fraction !== '') {
            if (inFlag) {
                result += '-';
            } else if (result !== '') {
                result += ' ';
            }

            inFlag = true;
            result += `${fraction}`;
          }

          if (inFlag) {
            result += 'in.';
          }
    
          return result.trim();
        }
    }

    static generateId(product: Partial<Product>): string {
        console.log(product);
        let concat_id = product.category;
        for (const attr of ProductDictionary.IdentifyingAttributes[product.category]) {
            if (attr === 'length' || attr === 'width' || attr === 'thickness') {
                const x = Number.isInteger(product[attr]) ? product[attr].toFixed(1) : product[attr].toString();
                concat_id += `${x}#` || '#';
            } else if (product[attr] == null || product[attr] === undefined) {
                concat_id += '#';
            } else {
                concat_id += `${product[attr]}#`;
            }
        }
        console.log(concat_id);
        const hashedId = shajs('sha256').update(concat_id.slice(0,-1)).digest('hex');
        return hashedId.slice(0, 10);
    }
}

export class LumberProduct extends Product {
    grade: string;
    profile: string;
    precision: string;
    fingerJoint: string;
    bdft: number;
    species: string;
    treatment: string;

    constructor(
        id: string,
        length: number,
        width: number,
        thickness: number,
        weight: number,
        facilityId: string,
        prices: number[][],
        grade: string,
        profile: string,
        precision: string,
        fingerJoint: string,
        bdft: number,
        species: string,
        priceType: string,
        heading: string,
        subheading: string,
        image: string,
        treatment?: string,
        inventory?: number,
        description?: string,
        brand?: string,
        origin?: string,
        metric?: any,
    ) {
        super(id, length, width, thickness, weight, facilityId, prices, priceType, heading, subheading, image, inventory, description, brand, origin, metric);
        this.grade = grade;
        this.profile = profile;
        this.precision = precision;
        this.fingerJoint = fingerJoint;
        this.bdft = Math.round(bdft*1000)/1000;
        this.species = species;
        this.treatment = treatment;
        this.category = 'lumber';
    }
}

export class SheetGoodProduct extends Product {
    panelType: string;
    grade?: string;
    species?: string;
    treatment?: string;
    edge?: string;
    finish?: string;

    constructor(
        id: string,
        length: number,
        width: number,
        thickness: number,
        weight: number,
        facilityId: string,
        prices: number[][],
        priceType: string,
        panelType: string,
        heading: string,
        subheading: string,
        image: string,
        treatment?: string,
        inventory?: number,
        description?: string,
        brand?: string,
        grade?: string,
        species?: string,
        edge?: string,
        finish?: string,
        origin?: string,
        metric?: any,
    ) {
        super(id, length, width, thickness, weight, facilityId, prices, priceType, heading, subheading, image, inventory, description, brand, origin, metric);
        this.category = 'sheet_good';
        this.panelType = panelType;
        this.grade = grade;
        this.species = species;
        this.treatment = treatment;
        this.edge = edge;
        this.finish = finish;
    }

    // this is an example use of metric - if you want to use it, you need to override to specify which dimension (L,W,T) is metric
    override get formattedThickness(): string {
        return Product.formatDistance(this.thickness, this.metric);
    }
}
