import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { LoadingComponent } from '../loading/loading.component';
import { NavService } from '../../services/nav.service';
import { PageCard } from '../../models/page-card.model';

@Component({
  selector: 'app-nav',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, LoadingComponent],
  templateUrl: './nav.component.html',
  styleUrls: ['./nav.component.scss']
})
export class NavComponent implements OnInit {
  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private navService: NavService
  ) { }

  page: string; // nav page or search
  id: string; // id of the nav page
  searchTerm: string; // search term from query string
  filters: {}; // filters from query string
  title: string; // title of the page

  cards: PageCard[] = []; // cards to display on the page

  isLoading: boolean = true;

  async ngOnInit() {
    this.page = this.route.snapshot.url[0].path;
    this.id = this.route.snapshot.paramMap.get('id');

    console.log(this.page, this.id);

    this.route.queryParams.subscribe(params => {
      if (Object.keys(params).length) {
        this.searchTerm = params['searchTerm'] ? decodeURIComponent(params['searchTerm']) : '';
        console.log("searchTerm: " + this.searchTerm);
  
        console.log(params);
      }
    });

    if (this.page === 'nav') {
      await this.loadPage();
    }
  
    this.isLoading = false;
  }

  async loadPage() {
    const res = await this.navService.getCardsById(this.id);
    this.title = res.title;
    this.cards = res.cards;

    if (res.filters) {
      this.filters = res.filters;
    }
    console.log(res);
  }

  searchProducts(event: Event) {
    event.preventDefault();
    const encodedSearchTerm = encodeURIComponent(this.searchTerm);
    this.router.navigate(['/search'], { queryParams: { searchTerm: encodedSearchTerm } });
  }

  navigate(link: string) {
    this.router.navigate([link]);
  }
}
