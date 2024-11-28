import { isPlatformBrowser } from '@angular/common';
import { Inject, Injectable, PLATFORM_ID } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class SessionStorageService {
    
    constructor(@Inject(PLATFORM_ID) private platformId: Object) { }

    // Sets an item in the SessionStorage map.
    setItem(key: string, value: string) {

        if (isPlatformBrowser(this.platformId)){
            sessionStorage.setItem(key, value);
        }
        
    }

    // Getter for an item in the SessionStorage map.
    getItem(key: string): string | null {

        if (isPlatformBrowser(this.platformId)){
           return sessionStorage.getItem(key);
        }
        
        return null;

    }

}