const { createApp } = Vue;

        createApp({
            data() {
                return {
                    currentTeam: 'Your Team',
                    apis: [],
                    filteredAPIs: [],
                    searchQuery: '',
                    selectedRisk: '',
                    selectedCatalog: '',
                    selectedCollection: '',
                    selectedAPI: null,
                    stats: {
                        total: 0,
                        total_apis: 0,
                        migrated: 0,
                        pending: 0,
                        failed: 0,
                        risk_distribution: { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 }
                    },
                    migrationStatus: {},
                    logs: [],
                    activeTab: 'discovery',
                    isGeneratingPlan: false,
                    generatedConfig: null,
                    migrationStep: 0,  // Track current migration step (0-5)
                    canaryPercentage: 0,  // Canary rollout percentage
                    platforms: {
                        apic: true,      // APIC enabled by default
                        kafka: false,
                        salesforce: false,
                        mulesoft: false
                    },
                    isDiscovering: false,
                    showGeneratedYAML: false,
                    riskChart: null,
                    showSettings: false
                }
            },
            computed: {
                migrationCount() {
                    return Object.values(this.migrationStatus).filter(s =>
                        s.status.includes('CANARY') || s.status === 'MIRRORING'
                    ).length;
                },
                completedCount() {
                    return Object.values(this.migrationStatus).filter(s =>
                        s.status === 'COMPLETED'
                    ).length;
                },
                hasAnyPlatformEnabled() {
                    return this.platforms.apic || this.platforms.kafka ||
                        this.platforms.salesforce || this.platforms.mulesoft;
                },
                enabledPlatforms() {
                    return Object.keys(this.platforms).filter(p => this.platforms[p]);
                }
            },
            methods: {
                async discoverAPIs() {
                    this.isDiscovering = true;

                    try {
                        const selectedPlatforms = Object.keys(this.platforms).filter(p => this.platforms[p]);

                        const response = await fetch('/api/discover', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ filters: [], platforms: selectedPlatforms })
                        });

                        const data = await response.json();
                        console.log('Discovered APIs:', data);

                        this.apis = data.apis || [];
                        this.filteredAPIs = [...this.apis];

                        // Update stats with risk distribution
                        const riskCounts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
                        this.apis.forEach(api => {
                            if (api.risk && api.risk.level) {
                                riskCounts[api.risk.level] = (riskCounts[api.risk.level] || 0) + 1;
                            }
                        });

                        this.stats = {
                            total: this.apis.length,
                            total_apis: this.apis.length,
                            migrated: 0,
                            pending: this.apis.length,
                            failed: 0,
                            risk_distribution: riskCounts
                        };

                        // Update risk chart
                        this.updateRiskChart();

                    } catch (error) {
                        console.error('Failed to discover APIs:', error);
                        alert('Failed to discover APIs: ' + error.message);
                    } finally {
                        this.isDiscovering = false;
                    }
                },
                copyToClipboard(text) {
                    navigator.clipboard.writeText(text).then(() => {
                        alert('Copied to clipboard!');
                    }).catch(err => {
                        console.error('Failed to copy:', err);
                    });
                },
                async refreshStatus() {
                    try {
                        const [statusResponse, logsResponse, statsResponse] = await Promise.all([
                            fetch('/api/status'),
                            fetch('/api/logs'),
                            fetch('/api/stats')
                        ]);

                        const statusData = await statusResponse.json();
                        const logsData = await logsResponse.json();
                        const statsData = await statsResponse.json();

                        this.migrationStatus = statusData.migrations;
                        this.logs = logsData.logs;
                        this.stats = statsData;

                        console.log('✅ Status refreshed:', {
                            migrations: Object.keys(statusData.migrations).length,
                            logs: logsData.logs.length,
                            apis: statsData.total_apis
                        });
                    } catch (error) {
                        console.error('❌ Failed to refresh status:', error);
                    }
                },
                selectAPI(api) {
                    this.selectedAPI = api;
                    this.generatedConfig = null;
                    this.migrationStep = 0;
                    this.canaryPercentage = 0;
                    this.showGeneratedYAML = false;
                },
                async generatePlan(apiName) {
                    this.isGeneratingPlan = true;
                    try {
                        const response = await fetch('/api/plan', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ api_name: apiName })
                        });
                        const data = await response.json();
                        this.generatedConfig = data.configs;
                    } catch (error) {
                        console.error('Plan generation failed:', error);
                        alert('Failed to generate plan');
                    } finally {
                        this.isGeneratingPlan = false;
                    }
                },
                downloadYAML(filename, content) {
                    try {
                        console.log('Downloading:', filename, 'Size:', content.length, 'chars');

                        const blob = new Blob([content], { type: 'application/x-yaml' });
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = filename;

                        document.body.appendChild(a);
                        a.click();

                        // Clean up after a short delay
                        setTimeout(() => {
                            document.body.removeChild(a);
                            window.URL.revokeObjectURL(url);
                            console.log('✅ Download initiated:', filename);
                        }, 100);

                    } catch (error) {
                        console.error('❌ Download failed:', error);
                        alert(`Failed to download ${filename}: ${error.message}`);
                    }
                },
                async startMirroring(apiName) {
                    try {
                        await fetch(`/api/migrate/${apiName} / mirror`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ duration_hours: 24 })
                        });
                        this.refreshStatus();
                    } catch (error) {
                        console.error('Failed to start mirroring:', error);
                    }
                },
                async shiftTraffic(apiName, percentage) {
                    try {
                        await fetch(`/api/migrate/${apiName}/shift`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ api_name: apiName, percentage: parseInt(percentage) })
                        });
                        this.refreshStatus();
                    } catch (error) {
                        console.error('Failed to shift traffic:', error);
                    }
                },
                async rollback(apiName) {
                    if (!confirm(`Rollback ${apiName}? This will send 100% traffic back to legacy platform.`)) {
                        return;
                    }
                    try {
                        await fetch(`/api/migrate/${apiName}/rollback`, { method: 'POST' });
                        this.refreshStatus();
                    } catch (error) {
                        console.error('Rollback failed:', error);
                    }
                },
                copyDeployCommands() {
                    const commands = [
                        '# Save YAML files to disk first, then:',
                        'kubectl apply -f virtualservice.yaml',
                        'kubectl apply -f upstream.yaml'
                    ];

                    if (this.generatedConfig && this.generatedConfig['authconfig.yaml']) {
                        commands.push('kubectl apply -f authconfig.yaml');
                    }
                    if (this.generatedConfig && this.generatedConfig['ratelimitconfig.yaml']) {
                        commands.push('kubectl apply -f ratelimitconfig.yaml');
                    }

                    navigator.clipboard.writeText(commands.join('\n')).then(() => {
                        alert('✅ Commands copied to clipboard!');
                    });
                },
                downloadAllConfigs() {
                    if (!this.generatedConfig) return;

                    // Create a zip-like download by creating individual files
                    for (const [filename, content] of Object.entries(this.generatedConfig)) {
                        const blob = new Blob([content], { type: 'text/yaml' });
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);
                    }

                    alert(`✅ Downloaded ${Object.keys(this.generatedConfig).length} YAML files`);
                },
                showMigrationWorkflow() {
                    // Show the migration workflow modal
                    this.migrationStep = 1;  // Start at step 1 (Deploy)
                    alert('🚀 Migration workflow starting! Follow the steps to deploy and migrate traffic.');
                },
                getRiskBadgeClass(level) {
                    const classes = {
                        'CRITICAL': 'bg-red-100 text-red-800',
                        'HIGH': 'bg-orange-100 text-orange-800',
                        'MEDIUM': 'bg-yellow-100 text-yellow-800',
                        'LOW': 'bg-green-100 text-green-800'
                    };
                    return classes[level] || 'bg-gray-100 text-gray-800';
                },
                getCatalogBadgeClass(catalog) {
                    const classes = {
                        'production': 'bg-blue-100 text-blue-800',
                        'sandbox': 'bg-purple-100 text-purple-800',
                        'development': 'bg-gray-100 text-gray-800',
                        'default': 'bg-gray-100 text-gray-600'
                    };
                    return classes[catalog] || classes['default'];
                },
                getCollectionBadgeClass(collection) {
                    const classes = {
                        'Customer Services': 'bg-green-100 text-green-700',
                        'Payment Services': 'bg-indigo-100 text-indigo-700',
                        'Order Management': 'bg-pink-100 text-pink-700',
                        'Partner APIs': 'bg-teal-100 text-teal-700',
                        'Internal Tools': 'bg-amber-100 text-amber-700',
                        'uncategorized': 'bg-gray-100 text-gray-600'
                    };
                    return classes[collection] || classes['uncategorized'];
                },
                getStatusBadgeClass(status) {
                    if (status === 'COMPLETED') return 'bg-green-100 text-green-800';
                    if (status === 'ROLLED_BACK') return 'bg-red-100 text-red-800';
                    if (status === 'MIRRORING') return 'bg-blue-100 text-blue-800';
                    return 'bg-yellow-100 text-yellow-800';
                },
                getLogColor(level) {
                    if (level === 'WARNING') return 'text-yellow-400';
                    if (level === 'ERROR') return 'text-red-400';
                    return 'text-green-400';
                },
                formatNumber(num) {
                    if (!num) return 'Unknown';
                    return num.toLocaleString();
                },
                formatTime(timestamp) {
                    return new Date(timestamp).toLocaleTimeString();
                },
                filterAPIs() {
                    this.filteredAPIs = this.apis.filter(api => {
                        // Search filter
                        const matchesSearch = !this.searchQuery ||
                            api.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                            (api.display_name && api.display_name.toLowerCase().includes(this.searchQuery.toLowerCase())) ||
                            api.basePath.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                            api.description.toLowerCase().includes(this.searchQuery.toLowerCase());

                        // Risk filter
                        const matchesRisk = !this.selectedRisk || api.risk.level === this.selectedRisk;

                        // Catalog filter
                        const matchesCatalog = !this.selectedCatalog || api.catalog === this.selectedCatalog;

                        // Collection filter
                        const matchesCollection = !this.selectedCollection || api.collection === this.selectedCollection;

                        return matchesSearch && matchesRisk && matchesCatalog && matchesCollection;
                    });

                    console.log(`Filtered: ${this.filteredAPIs.length} / ${this.apis.length} APIs`);
                },
                updateRiskChart() {
                    this.$nextTick(() => {
                        const ctx = document.getElementById('riskChart');
                        if (!ctx) return;

                        if (this.riskChart) {
                            this.riskChart.destroy();
                        }

                        this.riskChart = new Chart(ctx, {
                            type: 'bar',
                            data: {
                                labels: ['Critical', 'High', 'Medium', 'Low'],
                                datasets: [{
                                    label: 'Number of APIs',
                                    data: [
                                        this.stats.risk_distribution.CRITICAL,
                                        this.stats.risk_distribution.HIGH,
                                        this.stats.risk_distribution.MEDIUM,
                                        this.stats.risk_distribution.LOW
                                    ],
                                    backgroundColor: [
                                        'rgba(239, 68, 68, 0.8)',
                                        'rgba(249, 115, 22, 0.8)',
                                        'rgba(234, 179, 8, 0.8)',
                                        'rgba(34, 197, 94, 0.8)'
                                    ]
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: true,
                                plugins: {
                                    legend: { display: false }
                                }
                            }
                        });
                    });
                }
            },
            mounted() {
                // Auto-refresh status every 5 seconds
                setInterval(() => {
                    if (this.apis.length > 0) {
                        this.refreshStatus();
                    }
                }, 5000);
            }
        }).mount('#app'
