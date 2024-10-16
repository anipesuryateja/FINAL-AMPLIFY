import { Product } from './product.model';
import { ProductDictionary } from './product-dictionary.model';

export class ProductGroup {
  id: string; // pcid
  products: Record<string, Product[]>; // products indexed by SKU
  attributeMap: {}; // a map of uniquely identifying attributes to product ids

  constructor(id: string, products: Record<string, Product[]>) {
    this.id = id;
    this.products = products;
    this.parseAttributes();
  }

  get keys(): string[] {
    return Object.keys(this.products);
  }

  get category(): string {
    return this.products[this.keys[0]][0].category
  }

  parseAttributes(): void {
    const attributeMap: Record<string, any> = {};
  
    const attributes = ProductDictionary.IdentifyingAttributes[this.category];
  
    Object.values(this.products).forEach(productArray => {
      const product = productArray[0];
      let currentLevel = attributeMap;
      const levels: any[] = [];
  
      attributes.forEach(attr => {
        const value = product[attr] || "None";
        levels.push({ value, level: currentLevel });
  
        if (!currentLevel[value]) {
          currentLevel[value] = {};
        }
        currentLevel = currentLevel[value];
      });
  
      currentLevel["id"] = product.id.split('#').slice(-1)[0];
    });
  
    // Compress categories with only one product array
    const compressLevel = (level: any): any => {
      if (typeof level !== 'object' || !level) return level;
  
      const keys = Object.keys(level);
      if (keys.length === 1 && keys[0] !== 'id') {
        const singleKey = keys[0];
        const compressed = compressLevel(level[singleKey]);
        return compressed;
      }
  
      for (const key of keys) {
        level[key] = compressLevel(level[key]);
      }

      return level;
    };
  
    this.attributeMap = compressLevel(attributeMap);
  }

  getProductsBySKU(id: string): Product[] {
    if (!this.products[id]) {
      console.error(`ProductCard ${this.id} does not contain a product with SKU ${id}`);
      return [];
    }
    return this.products[id];
  }

  // The following two methods are to be used later in lazy loading:
  // load a single SKU
  loadSingleSKU(key: string, products: Product[]) {
    this.products[key] = products;
  }

  // load multiple SKUs
  loadProducts(productRecord: Record<string, Product[]>) {
    for (const key in productRecord) {
      this.loadSingleSKU(key, productRecord[key]);
    }
  }
}
