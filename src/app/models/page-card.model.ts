export class PageCard {
    title: string;
    subtitle: string;
    link: string;
    id: string;
    type: "product" | "group" | "nav";
    image?: string;

    constructor(id: string, title: string, type: "product" | "group" | "nav", subtitle?: string, image?: string) {
        this.title = title;
        this.subtitle = subtitle;
        this.image = image;
        this.type = type;
        this.id = id;

        if (type === "product") {
            this.link = "/product/" + id;
        } else if (type === "group") {
            this.link = "/product-group/" + id;
        } else if (type === "nav") {
            this.link = "/nav/" + id;
        }
    }
}
