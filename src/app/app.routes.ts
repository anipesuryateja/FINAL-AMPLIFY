import { Routes } from '@angular/router';
import { ProductComponent } from './public/product/product.component';
import { NotFoundComponent } from './public/not-found/not-found.component';
import { NavComponent } from './public/nav/nav.component';
import { HomeComponent } from './public/home/home.component';

export const routes: Routes = [
    { path: 'product/:id', component: ProductComponent },
    { path: 'product-group/:pgid', component: ProductComponent },
    { path: 'search', component: NavComponent },
    { path: 'home', component: HomeComponent },
    { path: 'nav/:id', component: NavComponent },
    { path: '', redirectTo: '/home', pathMatch: 'full' },
    { path: '**', component: NotFoundComponent },
];
