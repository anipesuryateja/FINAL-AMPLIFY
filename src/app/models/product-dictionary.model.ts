export const ProductDictionary = {
    // TODO: eventually consolidate all of the below with the attribute optionNames system in product component and a map of backend namespace
    DisplayAttributes: { 
        // These are the attributes that will be displayed in the product table, in order
        // values are of the form [key, display name]
        // These are handled with an @if that checks if they exist on the product object, so its safe to add sparse/optional
        all: [ // attributes for all products
            // most of these were removed because the identifiers are not common across attributes
            // e.g. hardware dimensions will be "Package Length, Package Width, Package Height" while lumber will be "Length, Width, Thickness"
            ['weight' , 'Item Weight (lbs.)'],
            ['inventory' , 'Pieces Available at this Price'],
        ],
        lumber: [
            ['brand', 'Brand'], 
            ['profile', 'Nominal Size'],
            ['grade', 'Grade'],
            ['precision', 'Precision End Trim'],
            ['fingerJoint', 'Finger Joint'],
            ['bdft', 'Board Footage'],
            ['species', 'Species'],
            ['treatment', 'Treatment'],
            ['formattedLength', 'Length'],
            ['formattedWidth', 'Width'],
            ['formattedThickness', 'Thickness'],
        ],
        sheet_good: [
            ['brand', 'Brand'],
            ['panelType', 'Panel Type'],
            ['grade', 'Grade'],
            ['species', 'Species'],
            ['treatment', 'Treatment'],
            ['edge', 'Edge'],
            ['finish', 'Finish'],
            ['origin', 'Origin'],
            ['formattedLength', 'Length'],
            ['formattedWidth', 'Width'],
            ['formattedThickness', 'Thickness'],
        ]
    },
    // the attrbutes which uniquely identify a product - those that go into its hashed id
    // these are ordered when generating a hashed id
    // they are also ordered by precedence when generating selectors on a product-card page
    IdentifyingAttributes: {
        lumber: ['length','profile','grade','species','fingerJoint','precision','treatment','brand'],
        sheet_good: ['length','width','thickness','species','grade','panelType','treatment','edge','finish','brand','origin','metric']
    },
    // TODO: find the best way to fold these into display attributes/make them derive from display attributes
    SelectorNames: {
        length: 'Length',
        profile: 'Nominal Size',
        grade: 'Grade',
        species: 'Species',
        fingerJoint: 'Finger Joint',
        precision: 'Precision End Trim',
        treatment: 'Treatment',
        brand: 'Brand',
        width: 'Width',
        thickness: 'Thickness',
        panelType: 'Panel Type',
        edge: 'Edge',
        finish: 'Finish',
        origin: 'Origin',
        metric: 'Metric',
    },
};
