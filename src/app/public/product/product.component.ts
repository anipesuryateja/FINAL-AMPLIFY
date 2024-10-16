import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ProductService } from '../../services/product.service';
import { Product } from '../../models/product.model';
import { ProductDictionary } from '../../models/product-dictionary.model';
import { ProductGroup } from '../../models/product-group.model';
import { NgIf, NgFor, NgClass } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LoadingComponent } from '../loading/loading.component';
import { NotFoundComponent } from '../not-found/not-found.component';

class QuantityButton {
  quantity: number;
  message: string;
}

class AttributeSelector {
  attrName: string; // human readable name for attribute
  attr: string; // the attribute identifier
  selection: any; // the current selection for this attribute (the one that is highlighted)
  options: any[]; // the possible values for this attribute
  parentChoices: {}; // the choices of higher up selectors on the page
  optionNames: {}; // the human readable names for the options, retrievable by option value - sparsely populated with option as a default
}

@Component({
  selector: 'app-product',
  standalone: true,
  imports: [NgIf, NgFor, FormsModule, LoadingComponent, NotFoundComponent, NgClass],
  templateUrl: './product.component.html',
  styleUrls: ['./product.component.scss']
})
export class ProductComponent implements OnInit {
  product: Product; // the product being displayed
  quantity: number;
  totalPrice: number;
  quantityButtons: QuantityButton[] = [];
  packSizes: number[] = []; // sorted list of all the pack sizes for the current product
  allProducts: ProductGroup; // all products displayable by the current PGID (or single product by id)

  selectors: AttributeSelector[] = [];

  isLoading: boolean = true;

  productId = null;
  pgid = null;

  formatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

  productDictionary = ProductDictionary;

  constructor(
    private route: ActivatedRoute,
    private productService: ProductService
  ) { }

  async ngOnInit() {
    this.productId = this.route.snapshot.paramMap.get('id');
    this.pgid = this.route.snapshot.paramMap.get('pgid');

    if (this.productId) {
      this.productId = this.productId.toLowerCase();
      const products = await this.productService.getProductById(this.productId);
      const productRecord = { [this.productId]: products };
      this.allProducts = new ProductGroup(
        this.productId,
        productRecord
      );
    } else if (this.pgid) {
      this.pgid = this.pgid.toLowerCase();
      this.allProducts = await this.productService.getProductsByPGID(this.pgid);
    }

    console.log(this.allProducts);

    this.setSelectors({});
    this.isLoading = false;
  }

  get packSizesString(): string {
    let res = '';
    for (const size of this.packSizes) {
      res += res? `, ${size}pc` : `${size}pc`;
    }
    return res;
  }

  get maxInventory(): number {
    let max = -1;
    for (const product of this.products) {
      if (product.inventory == null) {
        return Infinity;
      } else if (product.inventory > max) {
        max = product.inventory;
      }
    }

    return max;
  }

  get products(): Product[] {
    return this.allProducts.getProductsBySKU(this.productId);
  }

  setSelectors(choices: Record<string, any>) {
    this.selectors = [];
    let filteredProducts: Product[] = [];
    for (const key of this.allProducts.keys) {
      filteredProducts.push(this.allProducts.getProductsBySKU(key)[0]);
    }

    const parentChoices = {};
    const optionNames = {};
    for (const attr of ProductDictionary.IdentifyingAttributes[this.allProducts.category]) {
      const variants = new Set();

      for (const product of filteredProducts) {
        const s = variants.size;
        variants.add(product[attr]? product[attr] : 'None');
        
        // if a new option is added, assign it a human readable name, if applicable
        if (variants.size > s) {
          if (attr == 'length') {
            optionNames[product[attr]] = product.formattedLength;
          } else if (attr == 'width') {
            optionNames[product[attr]] = product.formattedWidth;
          } else if (attr == 'thickness') {
            optionNames[product[attr]] = product.formattedThickness;
          } 
          // else if (attr == 'species' && "species" in product) {
          //   optionNames[product[attr]] = product.species;
          // } else if (attr == 'grade' && "grade" in product) {
          //   optionNames[product[attr]] = product.grade;
          // } else if (attr == 'treatment' && "treatment" in product) {
          //   optionNames[product[attr]] = product.treatment;
          // }
        }
      }

      if (variants.size <= 1) continue;

      const values = Array.from(variants).sort((a, b) => {
        if (typeof a === 'number' && typeof b === 'number') {
          return a - b;
        } else {
          return a.toString().localeCompare(b.toString());
        }
      });

      this.selectors.push({
        attrName: ProductDictionary.SelectorNames[attr],
        attr,
        selection: choices[attr]? choices[attr] : this.makeChoice(attr, values),
        options: values,
        parentChoices: Object.assign({}, parentChoices),
        optionNames: Object.assign({}, optionNames),
      });

      parentChoices[attr] = this.selectors[this.selectors.length - 1].selection;

      filteredProducts = filteredProducts.filter(product => {
        const option = product[attr]? product[attr] : 'None';
        return option === this.selectors[this.selectors.length - 1].selection;
      });
    }

    let obj = this.allProducts.attributeMap;
    for (const selector of this.selectors) {
      obj = obj[selector.selection];
    }
    this.selectProduct(obj['id']);
  }

  makeChoice(attr: string, values: any[]): any {
    // Placeholder for marketing logic. In the future, we can keep a mapping of attributes to values that we want to 
    // prioritize on the backend and import it with getProductsByPGID. Selects random for now.
    const randomIndex = Math.floor(Math.random() * values.length);
    return values[randomIndex];
  }

  selectOption(selector: AttributeSelector, option: any) {
    const choices = selector.parentChoices;
    choices[selector.attr] = option;
    this.setSelectors(choices);
  }

  // this is the only function allowed to select a product (setting this.productId)
  selectProduct(id: string) {
    if (this.allProducts.keys.includes(id)) {
      this.productId = id;
    } else {
      console.error(`Product with id ${id} not found in product card`);
    }

    if (this.products.length) {
      let packSizes = new Set<number>();
      for (const product of this.products) {
        for (const price of product.prices) {
          packSizes.add(price.packSize);
        }
      }
      this.packSizes = Array.from(packSizes).sort((a, b) => a - b);

      this.setQuantity(1, true);
    }
  }

  getTableAttributes(): string[] {
    return [...ProductDictionary.DisplayAttributes[this.product.category], ...ProductDictionary.DisplayAttributes['all']];
  }
  
  // since we set the product to get the best total price, we must also update product here
  // THIS SHOULD BE THE ONLY PLACE IN THE COMPONENT WHERE product IS SET
  setTotalPrice() {
    [this.totalPrice, this.product] = this.getTotalPrice(this.quantity);
  }

  // return the total price for the quantity (across all suppliers) of the current product, and the product that gives that price
  // price is infinity if the quantity is not allowable
  // this is intentional, as the method is used to check allowable increments via the wrapper allowableQuantityIncrement
  getTotalPrice(quantity: number): [number, Product] {
    let minPrice = Infinity;
    let selectedProduct = null;
    for (const product of this.products) {
      if (quantity % product.prices[0].packSize == 0 && (product.inventory == null || product.inventory >= quantity)) {
        const price = this.getProductPrice(product, quantity);
        if (price < minPrice) {
          selectedProduct = product;
          minPrice = price;
        }
      }
    }
    return [minPrice, selectedProduct];
  }

  // return the best price that can be obtained for the given quantity of the given supplier-specific product
  getProductPrice(product: Product, q: number): number {
    let remainder = q;
    let res = 0;
    for (const price of product.prices.slice().reverse()) {
      const quotient = Math.floor(remainder / price.packSize);
      remainder = remainder % price.packSize;
      res += quotient * price.price * price.packSize;
    }
    return res;
  }

  // sets the quantity to value initially, then counts up or down to the next allowable quantity
  // the flag "increment" determines whether to increment or decrement to find the next allowable quantity
  setQuantity(value: any, increment: boolean) {
    let parsedValue = parseInt(value, 10);
    if (isNaN(parsedValue)) {
      this.setQuantity(1, true);
    }

    if (increment) {
      while (!this.allowableQuantityIncrement(parsedValue)) {
        parsedValue++;
        if (parsedValue > this.maxInventory) {
          this.setQuantity(this.maxInventory, false);
          return;
        }
      }
    } else {
      while (!this.allowableQuantityIncrement(parsedValue)) {
        parsedValue--;
        if (parsedValue < 1) {
          this.setQuantity(1, true);
          return;
        }
      }
    }
    
    this.quantity = parsedValue;
    this.setTotalPrice();
    this.setQuantityButtons();
  }

  // sets the quantity to the NEXT HIGHEST allowable quantity
  incrementQuantity() {
    this.setQuantity(this.quantity + 1, true);
  }
  
  // sets the quantity to the NEXT LOWEST allowable quantity
  decrementQuantity() {
    this.setQuantity(this.quantity - 1, false);
  }

  allowableQuantityIncrement(quantity: number): boolean {
    return quantity > 0 && this.getTotalPrice(quantity)[0] !== Infinity;
  }

  // Sets the global quantityButtons array to contain the savings-related buttons that should be displayed.
  // Since this is based upon getTotalPrice, it should be effective for all products and all priceTypes, assuming
  // getTotalPrice and getProductPrice are implemented correctly.
  setQuantityButtons() {
    this.quantityButtons = [];
    
    const currentTotalPrice = this.getTotalPrice(this.quantity)[0];
    const currentAvgPrice = currentTotalPrice / this.quantity;
    const epsilon = 0.01; // Small value to handle floating-point precision issues
  
    let maxQ = 0;
    for (let product of this.products) {
      const q = product.prices[product.prices.length - 1].packSize;
      if (q > maxQ) {
        maxQ = q;
      }
    }
    
    for (let q = this.quantity + 1; q <= this.quantity + maxQ; q++) {
      const qTotalPrice = this.getTotalPrice(q)[0];
      const qAvgPrice = qTotalPrice / q;
    
      if (qAvgPrice < currentAvgPrice - epsilon) {
        // Calculate the savings correctly
        const savings = (currentAvgPrice * q) - qTotalPrice;
        if (savings > epsilon) {
          // this will show the next quantity at which the average price is lower than the current average price
          this.quantityButtons.push({ quantity: q, message: `Save ${this.formatter.format(savings)} by rounding up to ${q} pieces` });
          break;
        }
      }
    }
    // push other types of discounts here
  }

  addToCart() {
    console.log('Adding to cart:', this.product, this.quantity);
  }
}
