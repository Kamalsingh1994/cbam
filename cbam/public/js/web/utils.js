frappe.provide("cbam.utils")

$.extend(cbam.utils, {
    
    new_doc(doc){
        frappe.call({
            method: "cbam.utils.create_new_doc",
            args:{doc: doc},
            freeze: true,
            freeze_message: `Creating new ${doc.doctype}, please wait....`,
            callback(r){
                msgprint(`New ${doc.doctype}: ${r.message.name} created`)
            }
        })
    },
    get_field_options(doc, fieldname, asList=true){
        return new Promise(function(resolve, reject) {            
            frappe.call({
                method: "cbam.utils.get_field_options",
                args:{
                    doc: doc, 
                    fieldname: fieldname
                },
                callback(r){
                    if(r.message && r.message.length > 0) {
                        let options = r.message
                        if(!asList) {
                            options = r.message.join("\n");
                        }  
                        resolve(options)
                    } else {
                        resolve([])
                    }
                }
            })
        })
    },

    _get_links(doctype, filters, fields){
       return new Promise(function(resolve, reject) {
            frappe.call({
                method: "cbam.utils.links.get_links",
                args:{
                    doctype: doctype,
                    filters: filters,
                    fields: fields
                },
                callback(r){
                    if(r.message){
                        resolve(r.message)
                    }
                }
            })
            
            
        });
    
    },
    async get_links(doctype, filters, fields){
        return await cbam.utils._get_links(doctype, filters, fields);
    },
    _get_installation(emission){
        return new Promise(function(resolve, reject) {
             frappe.call({
                 method: "cbam.utils.links.get_installation",
                 args:{
                    emission: emission
                 },
                 callback(r){
                     if(r.message){
                         resolve(r.message)
                     }
                 }
             })
             
             
         });
     
     },
     async get_installation(emission){
        return await cbam.utils._get_installation(emission);
    },
    set_local_storage(){
        
        frappe.call({
            method: "cbam.utils.get_supplier",
            args:{
                
            },
            callback(r){
                if(r.message){
                    localStorage.setItem("parent_supplier", r.message)
                }
            }
        })
    },
    get_parent_supplier(){
        
        if (!localStorage.getItem("parent_supplier")){
            cbam.utils.set_local_storage()  
        }
        return localStorage.getItem("parent_supplier")

    },
    
    /**
     * Centralized Highcharts loader to prevent duplicate loading and conflicts
     * Used by: Financial Exposure Forecast, Various Cost Comparisons, ETS Price Dashboard
     * 
     * This loader handles all edge cases:
     * - Prevents duplicate script loading
     * - Handles race conditions
     * - Waits for existing loads to complete
     * - Verifies Highcharts is fully initialized
     * - Handles CDN failures gracefully
     */
    loadHighcharts(callback) {
        // Debug logging (can be removed in production)
        const DEBUG = false; // Set to true for debugging client issues
        
        if (DEBUG) {
            console.log('[Highcharts Loader] Starting load check', {
                HighchartsExists: typeof window.Highcharts !== 'undefined',
                HighchartsChartFunction: typeof window.Highcharts?.chart === 'function',
                existingScripts: document.querySelectorAll('script[src*="highcharts.js"]').length
            });
        }
        
        // Check if Highcharts is already loaded and available
        if (typeof window.Highcharts !== 'undefined' && typeof window.Highcharts.chart === 'function') {
            if (DEBUG) console.log('[Highcharts Loader] Highcharts already loaded, using existing');
            // Small delay to ensure it's fully initialized
            setTimeout(() => {
                if (callback) callback();
            }, 0);
            return;
        }
        
        // Check if script is already being loaded (avoid duplicate loads)
        // Use a global flag to prevent race conditions
        if (!window._highchartsLoading) {
            window._highchartsLoading = {
                callbacks: [],
                script: null
            };
        }
        
        // If already loading, add callback to queue
        if (window._highchartsLoading.script) {
            if (DEBUG) console.log('[Highcharts Loader] Script already loading, queuing callback');
            window._highchartsLoading.callbacks.push(callback);
            return;
        }
        
        // Check if script tag already exists (from previous attempt or external source)
        const existingScript = document.querySelector('script[src*="highcharts.js"]');
        if (existingScript) {
            if (DEBUG) console.log('[Highcharts Loader] Script tag exists, waiting...');
            window._highchartsLoading.script = existingScript;
            window._highchartsLoading.callbacks.push(callback);
            
            // Wait for existing script to load
            let checkCount = 0;
            const maxChecks = 50; // 5 seconds max wait
            const checkInterval = setInterval(() => {
                checkCount++;
                if (typeof window.Highcharts !== 'undefined' && typeof window.Highcharts.chart === 'function') {
                    clearInterval(checkInterval);
                    if (DEBUG) console.log('[Highcharts Loader] Existing script loaded successfully');
                    // Execute all queued callbacks
                    const callbacks = window._highchartsLoading.callbacks;
                    window._highchartsLoading = null;
                    callbacks.forEach(cb => {
                        if (cb) setTimeout(() => cb(), 100);
                    });
                } else if (checkCount >= maxChecks) {
                    clearInterval(checkInterval);
                    console.warn('[Highcharts Loader] Highcharts failed to load after timeout', {
                        checkCount,
                        HighchartsExists: typeof window.Highcharts !== 'undefined',
                        scriptComplete: existingScript.complete,
                        scriptReadyState: existingScript.readyState
                    });
                    // Execute callbacks with error
                    const callbacks = window._highchartsLoading.callbacks;
                    window._highchartsLoading = null;
                    callbacks.forEach(cb => {
                        if (cb) cb(new Error('Highcharts failed to load'));
                    });
                }
            }, 100);
            return;
        }
        
        // Load Highcharts script (new load)
        if (DEBUG) console.log('[Highcharts Loader] Creating new script tag');
        const script = document.createElement('script');
        script.src = 'https://code.highcharts.com/highcharts.js';
        script.async = true;
        script.id = 'cbam-highcharts-loader'; // Add ID for easier debugging
        
        // Mark as loading and queue callback
        window._highchartsLoading.script = script;
        window._highchartsLoading.callbacks.push(callback);
        
        script.onload = () => {
            if (DEBUG) console.log('[Highcharts Loader] Script onload fired');
            // Verify Highcharts is actually loaded before calling callback
            if (typeof window.Highcharts !== 'undefined' && typeof window.Highcharts.chart === 'function') {
                if (DEBUG) console.log('[Highcharts Loader] Highcharts verified and ready');
                // Execute all queued callbacks
                const callbacks = window._highchartsLoading.callbacks;
                window._highchartsLoading = null;
                // Small delay to ensure Highcharts is fully initialized
                callbacks.forEach(cb => {
                    if (cb) setTimeout(() => cb(), 100);
                });
            } else {
                console.error('[Highcharts Loader] Script loaded but Highcharts not available', {
                    HighchartsExists: typeof window.Highcharts !== 'undefined',
                    HighchartsType: typeof window.Highcharts,
                    chartFunction: typeof window.Highcharts?.chart
                });
                // Execute callbacks with error
                const callbacks = window._highchartsLoading.callbacks;
                window._highchartsLoading = null;
                callbacks.forEach(cb => {
                    if (cb) cb(new Error('Highcharts failed to initialize'));
                });
            }
        };
        script.onerror = (error) => {
            console.error('[Highcharts Loader] Script load error', error);
            // Execute callbacks with error
            const callbacks = window._highchartsLoading.callbacks;
            window._highchartsLoading = null;
            callbacks.forEach(cb => {
                if (cb) cb(new Error('Failed to load Highcharts'));
            });
        };
        document.head.appendChild(script);
        if (DEBUG) console.log('[Highcharts Loader] Script tag appended to head');
    }
            
        
})
