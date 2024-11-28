import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ResultsComponent } from './components/results/results.component';
import { NotFoundComponent } from './components/not-found/not-found.component';

export const routes: Routes = [
    {path: '', component: ResultsComponent},
    {path: '404', component: NotFoundComponent},
    {path: 'results', component: ResultsComponent},
    {path: '**', redirectTo: '/404'}
];

@NgModule({
    imports: [RouterModule.forRoot(routes)],
    exports: [RouterModule]
  })
  export class AppRoutingModule {
}
  