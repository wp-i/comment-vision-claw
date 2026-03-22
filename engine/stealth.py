"""
Stealth mode implementation for Playwright.

This module provides functions to make Playwright browsers less detectable
by implementing various evasion techniques specifically tailored for Chinese websites.
"""

import random
import time
import json
from datetime import datetime

def apply_stealth_mode(page):
    """
    Apply stealth mode to a Playwright page to avoid detection.
    
    Args:
        page: Playwright page object.
    """
    # Execute JavaScript to modify browser fingerprinting
    page.add_init_script("""
    () => {
        // Override property descriptors
        const overridePropertyDescriptor = (obj, prop, descriptorOverrides) => {
            const descriptor = Object.getOwnPropertyDescriptor(obj, prop);
            if (descriptor) {
                Object.defineProperty(obj, prop, { ...descriptor, ...descriptorOverrides });
            }
        };

        // Pass WebDriver test
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
            enumerable: true,
            configurable: true
        });
        
        // Pass Chrome test with more complete implementation
        window.chrome = {
            app: {
                InstallState: 'hehe',
                RunningState: 'running',
                isInstalled: false,
                getDetails: function() {},
                getIsInstalled: function() {},
                runningState: function() {}
            },
            runtime: {
                OnInstalledReason: {
                    INSTALL: 'install',
                    UPDATE: 'update',
                    CHROME_UPDATE: 'chrome_update',
                    SHARED_MODULE_UPDATE: 'shared_module_update'
                },
                OnRestartRequiredReason: {
                    APP_UPDATE: 'app_update',
                    OS_UPDATE: 'os_update',
                    PERIODIC: 'periodic'
                },
                PlatformArch: {
                    ARM: 'arm',
                    ARM64: 'arm64',
                    MIPS: 'mips',
                    MIPS64: 'mips64',
                    X86_32: 'x86-32',
                    X86_64: 'x86-64'
                },
                PlatformNaclArch: {
                    ARM: 'arm',
                    MIPS: 'mips',
                    MIPS64: 'mips64',
                    X86_32: 'x86-32',
                    X86_64: 'x86-64'
                },
                PlatformOs: {
                    ANDROID: 'android',
                    CROS: 'cros',
                    LINUX: 'linux',
                    MAC: 'mac',
                    OPENBSD: 'openbsd',
                    WIN: 'win'
                },
                RequestUpdateCheckStatus: {
                    THROTTLED: 'throttled',
                    NO_UPDATE: 'no_update',
                    UPDATE_AVAILABLE: 'update_available'
                }
            },
            webstore: {
                install: function() {},
                onDownloadProgress: {
                    addListener: function() {}
                },
                onInstallStageChanged: {
                    addListener: function() {}
                }
            }
        };
        
        // Pass Permissions test
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => {
            if (parameters.name === 'notifications' || 
                parameters.name === 'clipboard-read' || 
                parameters.name === 'clipboard-write') {
                return Promise.resolve({ state: Notification.permission, onchange: null });
            }
            return originalQuery(parameters);
        };
        
        // Prevent fingerprinting via canvas with more realistic noise
        const getImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function (x, y, w, h) {
            const imageData = getImageData.call(this, x, y, w, h);
            
            // Only add noise to specific canvas operations that might be used for fingerprinting
            const canvas = this.canvas;
            if (canvas && (w > 16 || h > 16)) {
                // Add very subtle noise to prevent fingerprinting but maintain visual quality
                for (let i = 0; i < imageData.data.length; i += 4) {
                    // Only modify 1 in 10 pixels to maintain visual quality
                    if (Math.random() < 0.1) {
                        const noise = Math.floor(Math.random() * 3) - 1;
                        imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise));
                        imageData.data[i+1] = Math.max(0, Math.min(255, imageData.data[i+1] + noise));
                        imageData.data[i+2] = Math.max(0, Math.min(255, imageData.data[i+2] + noise));
                    }
                }
            }
            return imageData;
        };
        
        // Override toDataURL to add noise
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
            // Add a tiny bit of randomness to the canvas before converting to data URL
            const ctx = this.getContext('2d');
            if (ctx && this.width > 16 && this.height > 16) {
                ctx.fillStyle = 'rgba(255, 255, 255, 0.001)';
                ctx.fillRect(
                    Math.random() * this.width, 
                    Math.random() * this.height, 
                    1, 
                    1
                );
            }
            return toDataURL.apply(this, arguments);
        };
        
        // Prevent fingerprinting via AudioContext with more realistic noise
        const getChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function (channel) {
            const channelData = getChannelData.call(this, channel);
            
            // Only add noise to longer audio samples that might be used for fingerprinting
            if (channelData.length > 1000) {
                // Add very subtle noise to prevent fingerprinting but maintain audio quality
                for (let i = 0; i < channelData.length; i += 500) {
                    if (Math.random() < 0.1 && channelData[i] !== 0) {
                        const noise = Math.random() * 0.0001;
                        channelData[i] += noise;
                    }
                }
            }
            return channelData;
        };
        
        // Create a more realistic plugins array
        const pluginsArray = [
            { description: "Chrome PDF Plugin", filename: "internal-pdf-viewer", name: "Chrome PDF Plugin" },
            { description: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai", name: "Chrome PDF Viewer" },
            { description: "Native Client", filename: "internal-nacl-plugin", name: "Native Client" }
        ];
        
        // Pass plugins length test with more realistic implementation
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = {
                    length: pluginsArray.length,
                    item: (index) => pluginsArray[index] || null,
                    namedItem: (name) => pluginsArray.find(p => p.name === name) || null,
                    refresh: () => undefined,
                    [Symbol.iterator]: function* () {
                        for (const plugin of pluginsArray) {
                            yield plugin;
                        }
                    }
                };
                
                // Add indexed properties
                for (let i = 0; i < pluginsArray.length; i++) {
                    Object.defineProperty(plugins, i, {
                        value: pluginsArray[i],
                        enumerable: true,
                        writable: false,
                        configurable: true
                    });
                }
                
                // Add named properties
                for (const plugin of pluginsArray) {
                    Object.defineProperty(plugins, plugin.name, {
                        value: plugin,
                        enumerable: false,
                        writable: false,
                        configurable: true
                    });
                }
                
                return plugins;
            },
            enumerable: true,
            configurable: true
        });
        
        // Pass mimeTypes test
        const mimeTypesArray = [
            { type: "application/pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: { name: "Chrome PDF Plugin" } },
            { type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: { name: "Chrome PDF Viewer" } },
            { type: "application/x-nacl", suffixes: "", description: "Native Client Executable", enabledPlugin: { name: "Native Client" } },
            { type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable", enabledPlugin: { name: "Native Client" } }
        ];
        
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => {
                const mimeTypes = {
                    length: mimeTypesArray.length,
                    item: (index) => mimeTypesArray[index] || null,
                    namedItem: (name) => mimeTypesArray.find(mt => mt.type === name) || null,
                    [Symbol.iterator]: function* () {
                        for (const mimeType of mimeTypesArray) {
                            yield mimeType;
                        }
                    }
                };
                
                // Add indexed properties
                for (let i = 0; i < mimeTypesArray.length; i++) {
                    Object.defineProperty(mimeTypes, i, {
                        value: mimeTypesArray[i],
                        enumerable: true,
                        writable: false,
                        configurable: true
                    });
                }
                
                // Add named properties
                for (const mimeType of mimeTypesArray) {
                    Object.defineProperty(mimeTypes, mimeType.type, {
                        value: mimeType,
                        enumerable: false,
                        writable: false,
                        configurable: true
                    });
                }
                
                return mimeTypes;
            },
            enumerable: true,
            configurable: true
        });
        
        // Pass languages test with Chinese as primary language
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en'],
            enumerable: true,
            configurable: true
        });
        
        // Modify platform to appear as Windows
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32',
            enumerable: true,
            configurable: true
        });
        
        // Add touch support
        Object.defineProperty(navigator, 'maxTouchPoints', {
            get: () => 5,
            enumerable: true,
            configurable: true
        });
        
        // Add hardware concurrency (CPU cores)
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
            enumerable: true,
            configurable: true
        });
        
        // Add device memory
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
            enumerable: true,
            configurable: true
        });
        
        // Add connection type
        if (!navigator.connection) {
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    rtt: 50 + Math.floor(Math.random() * 10),
                    downlink: 10 + Math.random() * 5,
                    effectiveType: '4g',
                    saveData: false,
                    onchange: null
                }),
                enumerable: true,
                configurable: true
            });
        }
        
        // Add WebGL support with more realistic values
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // UNMASKED_VENDOR_WEBGL
            if (parameter === 37445) {
                return 'Google Inc. (Intel)';
            }
            // UNMASKED_RENDERER_WEBGL
            if (parameter === 37446) {
                return 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)';
            }
            
            // Add more realistic WebGL parameters
            if (parameter === 3415) { // MAX_VERTEX_UNIFORM_VECTORS
                return 1024;
            }
            if (parameter === 3411) { // MAX_VERTEX_TEXTURE_IMAGE_UNITS
                return 16;
            }
            if (parameter === 3412) { // MAX_VARYING_VECTORS
                return 30;
            }
            if (parameter === 3414) { // MAX_FRAGMENT_UNIFORM_VECTORS
                return 1024;
            }
            if (parameter === 34921) { // MAX_VERTEX_ATTRIBS
                return 16;
            }
            if (parameter === 34930) { // MAX_TEXTURE_IMAGE_UNITS
                return 16;
            }
            if (parameter === 35661) { // MAX_COMBINED_TEXTURE_IMAGE_UNITS
                return 32;
            }
            if (parameter === 36349) { // MAX_DRAW_BUFFERS_WEBGL
                return 8;
            }
            
            return getParameter.apply(this, arguments);
        };
        
        // Override getExtension to provide all commonly available extensions
        const getExtension = WebGLRenderingContext.prototype.getExtension;
        WebGLRenderingContext.prototype.getExtension = function(name) {
            // Ensure common extensions are available
            const commonExtensions = [
                'ANGLE_instanced_arrays',
                'EXT_blend_minmax',
                'EXT_color_buffer_half_float',
                'EXT_disjoint_timer_query',
                'EXT_float_blend',
                'EXT_frag_depth',
                'EXT_shader_texture_lod',
                'EXT_texture_compression_bptc',
                'EXT_texture_compression_rgtc',
                'EXT_texture_filter_anisotropic',
                'OES_element_index_uint',
                'OES_fbo_render_mipmap',
                'OES_standard_derivatives',
                'OES_texture_float',
                'OES_texture_float_linear',
                'OES_texture_half_float',
                'OES_texture_half_float_linear',
                'OES_vertex_array_object',
                'WEBGL_color_buffer_float',
                'WEBGL_compressed_texture_astc',
                'WEBGL_compressed_texture_etc',
                'WEBGL_compressed_texture_etc1',
                'WEBGL_compressed_texture_pvrtc',
                'WEBGL_compressed_texture_s3tc',
                'WEBGL_compressed_texture_s3tc_srgb',
                'WEBGL_debug_renderer_info',
                'WEBGL_debug_shaders',
                'WEBGL_depth_texture',
                'WEBGL_draw_buffers',
                'WEBGL_lose_context',
                'WEBGL_multi_draw'
            ];
            
            if (commonExtensions.includes(name)) {
                const result = getExtension.call(this, name);
                if (result) {
                    return result;
                }
                // If the extension is not actually available, return a mock object
                return {};
            }
            
            return getExtension.call(this, name);
        };
        
        // Override performance.now() to add slight randomness
        const originalNow = performance.now;
        performance.now = function() {
            return originalNow.call(performance) + Math.random() * 0.01;
        };
        
        // Override Date.now() to add slight randomness
        const originalDateNow = Date.now;
        Date.now = function() {
            return originalDateNow() + Math.random() * 0.01;
        };
        
        // Add Baidu and Douyin specific properties that their detection systems check for
        window.Baidu = { version: '1.0.0' };
        window.byted_acrawler = { init: function() {} };
        window._bd_share_main = { init: function() {} };
        
        // Add common Chinese browser properties
        window.QQBrowser = { version: '10.8.4425.400' };
        window.ucweb = { version: '1.0.0' };
        window.ucbrowser = { version: '1.0.0' };
        
        // Add common Chinese payment APIs
        window.AlipayJSBridge = { call: function() {} };
        window.WeixinJSBridge = { invoke: function() {} };
    }
    """)
    
    # Set a more realistic user agent for Chinese websites with randomized components
    chrome_version = f"Chrome/{random.randint(90, 120)}.0.{random.randint(4000, 5000)}.{random.randint(100, 200)}"
    
    page.set_extra_http_headers({
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) {chrome_version} Safari/537.36',
        'sec-ch-ua': f'"Google Chrome";v="{chrome_version.split("/")[1].split(".")[0]}", "Chromium";v="{chrome_version.split("/")[1].split(".")[0]}", ";Not A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    })
    
    # Note: Geolocation should be set at the context level, not page level
    # We'll skip this here since it's already set in the browser setup
    
    # Grant permissions that a normal user would have
    try:
        page.context.grant_permissions(['geolocation', 'notifications'])
    except Exception:
        # If permissions can't be granted, continue anyway
        pass

def add_human_behavior(page):
    """
    Add human-like behavior to avoid bot detection.
    
    Args:
        page: Playwright page object.
    """
    # Random mouse movements
    def random_mouse_movement():
        viewport_size = page.viewport_size
        if viewport_size:
            width, height = viewport_size["width"], viewport_size["height"]
            for _ in range(random.randint(3, 8)):
                x = random.randint(0, width)
                y = random.randint(0, height)
                page.mouse.move(x, y)
                time.sleep(random.uniform(0.1, 0.5))
    
    # Random scrolling
    def random_scrolling():
        page.evaluate("""
            () => {
                const scrollHeight = document.body.scrollHeight;
                const viewportHeight = window.innerHeight;
                const scrollSteps = Math.floor(Math.random() * 5) + 3;
                const stepSize = (scrollHeight - viewportHeight) / scrollSteps;
                
                let currentScroll = 0;
                const scrollInterval = setInterval(() => {
                    if (currentScroll >= scrollHeight - viewportHeight) {
                        clearInterval(scrollInterval);
                        return;
                    }
                    
                    currentScroll += stepSize;
                    window.scrollTo(0, currentScroll);
                }, Math.floor(Math.random() * 500) + 500);
            }
        """)
        time.sleep(random.uniform(1, 3))
    
    # Execute these behaviors
    random_mouse_movement()
    random_scrolling()

def simulate_human_typing(element, text, min_delay=50, max_delay=150):
    """
    Simulate human typing with variable delays between keystrokes.
    
    Args:
        element: Playwright element to type into.
        text: Text to type.
        min_delay: Minimum delay between keystrokes in milliseconds.
        max_delay: Maximum delay between keystrokes in milliseconds.
    """
    for char in text:
        element.type(char, delay=random.randint(min_delay, max_delay))
        # Occasionally pause for a longer time
        if random.random() < 0.1:
            time.sleep(random.uniform(0.1, 0.3))
