// tests/javascript/playlist_detail.test.js

// Polyfill for TextEncoder/TextDecoder
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

const { JSDOM } = require('jsdom');

// Helper to set up DOM and run script logic for tests
function setupDOM(html) {
    const dom = new JSDOM(html);
    const window = dom.window;
    const document = window.document;

    // Make them global for the script logic redefined below, as the original script expects them to be global.
    global.window = window;
    global.document = document;
    global.bootstrap = { Toast: jest.fn().mockImplementation(() => ({ show: jest.fn(), dispose: jest.fn() })) };
    global.fetch = jest.fn();
    global.showToast = jest.fn();

    // --- Re-define core JavaScript logic from playlist_detail.html ---
    const getCellValue = (tr, cellIndex) => {
        const cell = tr.children[cellIndex];
        return cell ? (cell.innerText || cell.textContent || '').trim() : '';
    };

    const comparer = (idx, asc, sortType) => (a, b) => {
        let v1 = getCellValue(asc ? a : b, idx);
        let v2 = getCellValue(asc ? b : a, idx);
        if (sortType === 'number' || sortType === 'score') {
            v1 = parseFloat(v1.replace('%', '')) || (v1.toLowerCase() === 'n/a' ? -Infinity : 0);
            v2 = parseFloat(v2.replace('%', '')) || (v2.toLowerCase() === 'n/a' ? -Infinity : 0);
            return v1 - v2; // Direct numeric comparison
        } else if (sortType === 'duration') {
            const parseDuration = (durationStr) => {
                if (durationStr.toLowerCase() === 'n/a') return 0;
                const parts = durationStr.split(':').map(Number);
                return (parts.length === 2) ? (parts[0] * 60 + parts[1]) : 0;
            };
            v1 = parseDuration(v1);
            v2 = parseDuration(v2);
            return v1 - v2; // Direct numeric comparison
        }
        // For string and other types, localeCompare handles them well
        return v1.toString().localeCompare(v2.toString(), undefined, { sensitivity: 'base' });
    };

    function initializePlaylistDetailEventListeners() {
        const localShowToast = global.showToast;

        document.querySelectorAll('.sortable-header').forEach(headerCell => {
            headerCell.addEventListener('click', () => {
                const tableElement = headerCell.closest('table');
                const tbody = tableElement.querySelector('tbody#songTableBody');
                if (!tbody) return;

                const columnIdx = Array.from(headerCell.parentNode.children).indexOf(headerCell);
                const sortType = headerCell.dataset.sortType || 'string';

                let newAsc;
                if (headerCell.classList.contains('sorted-asc')) {
                    newAsc = false; // Was ascending, now descending
                } else if (headerCell.classList.contains('sorted-desc')) {
                    newAsc = true;  // Was descending, now ascending (or reset to ascending)
                } else {
                    newAsc = true;  // Not sorted, default to ascending
                }

                tableElement.querySelectorAll('.sortable-header').forEach(th => {
                    th.classList.remove('sorted-asc', 'sorted-desc');
                    const icon = th.querySelector('i.fas');
                    if (icon) icon.className = 'fas fa-sort ms-1';
                });

                headerCell.classList.toggle('sorted-asc', newAsc);
                headerCell.classList.toggle('sorted-desc', !newAsc);
                const icon = headerCell.querySelector('i.fas');
                if (icon) icon.className = newAsc ? 'fas fa-sort-up ms-1' : 'fas fa-sort-down ms-1';

                Array.from(tbody.querySelectorAll('tr'))
                    .sort(comparer(columnIdx, newAsc, sortType))
                    .forEach(tr => tbody.appendChild(tr));
            });
        });

        const songFilterInput = document.getElementById('songFilterInput');
        const songTableBody = document.getElementById('songTableBody');
        if (songFilterInput && songTableBody) {
            songFilterInput.addEventListener('keyup', function () {
                const searchTerm = songFilterInput.value.toLowerCase();
                const rows = songTableBody.querySelectorAll('tr');
                rows.forEach(row => {
                    const albumName = (row.children[2] && row.children[2].textContent || '').toLowerCase();
                    const songTitle = (row.children[3] && row.children[3].querySelector('strong.song-title')?.textContent || '').toLowerCase();
                    const artists = (row.children[4] && row.children[4].textContent || '').toLowerCase();
                    const status = (row.children[6] && row.children[6].textContent || '').toLowerCase();
                    if (albumName.includes(searchTerm) || songTitle.includes(searchTerm) || artists.includes(searchTerm) || status.includes(searchTerm)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            });
        }

        const analyzePlaylistButton = document.getElementById('analyzePlaylistBtn');
        if (analyzePlaylistButton) {
            analyzePlaylistButton.addEventListener('click', function () {
                const playlistId = this.dataset.playlistId;
                localShowToast(`Initiating analysis for playlist ${playlistId}... (Frontend Only Demo)`, 'info');
            });
        }

        document.querySelectorAll('.quick-action-btn').forEach(button => {
            button.addEventListener('click', function () {
                const songId = this.dataset.songId;
                const action = this.dataset.action;
                const actionCell = this.closest('td');
                const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]'); // Uses global document
                const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute('content') : null;
                if (!csrfToken) {
                    localShowToast('Critical error: CSRF token missing. Please refresh.', 'danger');
                    return;
                }
                global.fetch(`/api/song/${songId}/${action}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                })
                .then(response => {
                    if (!response.ok) return response.json().catch(() => { throw new Error(`HTTP error! ${response.status}`) }).then(err => { throw err; });
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        const newStatus = data.new_status;
                        actionCell.innerHTML = '';
                        if (newStatus === 'whitelisted') {
                            actionCell.innerHTML = `<button class="btn btn-sm btn-outline-secondary disabled" disabled title="Song is whitelisted"><i class="bi bi-check-circle-fill text-success"></i> <span class="d-none d-md-inline">Whitelisted</span></button>`;
                        } else if (newStatus === 'blacklisted') {
                            actionCell.innerHTML = `<button class="btn btn-sm btn-outline-secondary disabled" disabled title="Song is blacklisted"><i class="bi bi-x-octagon-fill text-danger"></i> <span class="d-none d-md-inline">Blacklisted</span></button>`;
                        } else {
                            actionCell.innerHTML = '<span class="text-muted">Status Updated</span>';
                        }
                        localShowToast(data.message, 'success');
                    } else {
                        throw new Error(data.message || 'API returned success:false');
                    }
                })
                .catch(error => {
                    localShowToast(error.message || 'Network error or API issue.', 'danger');
                });
            });
        });
    }
    // --- End of Re-defined script logic ---

    initializePlaylistDetailEventListeners(); // This ensures event listeners are set up on the global.document

    // Return the specific instances for tests to use, plus the functions themselves if needed directly.
    return { document, window, getCellValue, comparer };
}


describe('Playlist Detail Page JavaScript', () => {
    const baseHtml = `
        <meta name="csrf-token" content="test-csrf-token">
        <input type="text" id="songFilterInput" placeholder="Filter songs">
        <button id="analyzePlaylistBtn" data-playlist-id="pl123">Analyze Entire Playlist</button>
        <table>
            <thead>
                <tr>
                    <th class="sortable-header" data-sort-type="number"># <i class="fas fa-sort ms-1"></i></th>
                    <th>Album Art</th>
                    <th class="sortable-header" data-sort-type="string">Album Name <i class="fas fa-sort ms-1"></i></th>
                    <th class="sortable-header" data-sort-type="string">Song Title <i class="fas fa-sort ms-1"></i></th>
                    <th class="sortable-header" data-sort-type="string">Artist(s) <i class="fas fa-sort ms-1"></i></th>
                    <th class="sortable-header" data-sort-type="duration">Duration <i class="fas fa-sort ms-1"></i></th>
                    <th class="sortable-header" data-sort-type="string">Status <i class="fas fa-sort ms-1"></i></th>
                    <th class="sortable-header" data-sort-type="score">Score <i class="fas fa-sort ms-1"></i></th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="songTableBody">
                <tr>
                    <td>1</td>
                    <td><img src="art1.jpg"></td>
                    <td>Album Alpha</td>
                    <td><strong class="song-title">Song Foo</strong></td>
                    <td>Artist X</td>
                    <td>3:30</td>
                    <td>Pending</td>
                    <td>80%</td>
                    <td><button class="quick-action-btn" data-song-id="s1" data-action="whitelist">W</button></td>
                </tr>
                <tr>
                    <td>2</td>
                    <td><img src="art2.jpg"></td>
                    <td>Album Beta</td>
                    <td><strong class="song-title">Song Bar</strong></td>
                    <td>Artist Y</td>
                    <td>N/A</td>
                    <td>Analyzed</td>
                    <td>N/A</td>
                    <td><button class="quick-action-btn" data-song-id="s2" data-action="blacklist">B</button></td>
                </tr>
                <tr>
                    <td>3</td>
                    <td><img src="art3.jpg"></td>
                    <td>Album Gamma</td>
                    <td><strong class="song-title">Song Baz</strong></td>
                    <td>Artist Z</td>
                    <td>0:45</td>
                    <td>Whitelisted</td>
                    <td>50%</td>
                    <td><button class="quick-action-btn" data-song-id="s3" data-action="whitelist">W</button></td>
                </tr>
            </tbody>
        </table>
    `;

    let doc, win, getCellValueFromSetup, comparerFromSetup;

    beforeEach(() => {
        const setup = setupDOM(baseHtml);
        doc = setup.document; // Use this document for querying
        win = setup.window;   // Use this window for events
        getCellValueFromSetup = setup.getCellValue;
        comparerFromSetup = setup.comparer;

        global.fetch.mockClear();
        global.showToast.mockClear();
        // Clear mock calls on the bootstrap.Toast instance methods
        if (global.bootstrap && global.bootstrap.Toast.mock && global.bootstrap.Toast.mock.results[0]) {
            global.bootstrap.Toast.mock.results[0].value.show.mockClear();
        }
    });

    describe('getCellValue', () => {
        test('should get text content from a cell', () => {
            // console.log('Current DOM state for getCellValue test:', doc.body.innerHTML.substring(0,500)); // Temporary debug
            const row = doc.querySelector('#songTableBody tr'); // Use doc
            expect(row).not.toBeNull();
            expect(getCellValueFromSetup(row, 0)).toBe('1');
            expect(getCellValueFromSetup(row, 2)).toBe('Album Alpha');
        });
    });

    describe('comparer', () => {
        const mockRow = (cells) => {
            const tr = doc.createElement('tr'); // Use doc
            cells.forEach(text => {
                const td = doc.createElement('td'); // Use doc
                td.textContent = text;
                tr.appendChild(td);
            });
            return tr;
        };

        test('should compare numbers correctly', () => {
            const r1 = mockRow(['10']);
            const r2 = mockRow(['2']);
            expect(comparerFromSetup(0, true, 'number')(r1, r2)).toBeGreaterThan(0);
            expect(comparerFromSetup(0, false, 'number')(r1, r2)).toBeLessThan(0);
        });

        test('should compare strings correctly', () => {
            const r1 = mockRow(['Charlie']);
            const r2 = mockRow(['Alpha']);
            expect(comparerFromSetup(0, true, 'string')(r1, r2)).toBeGreaterThan(0);
            expect(comparerFromSetup(0, false, 'string')(r1, r2)).toBeLessThan(0);
        });

        test('should compare durations (mm:ss) correctly', () => {
            const r1 = mockRow(['2:30']);
            const r2 = mockRow(['1:00']);
            const r3 = mockRow(['N/A']);
            expect(comparerFromSetup(0, true, 'duration')(r1, r2)).toBeGreaterThan(0);
            expect(comparerFromSetup(0, true, 'duration')(r2, r3)).toBeGreaterThan(0);
        });

        test('should compare scores (percentages, N/A) correctly', () => {
            const r1 = mockRow(['75%']);
            const r2 = mockRow(['100%']);
            const r3 = mockRow(['N/A']);
            expect(comparerFromSetup(0, true, 'score')(r1, r2)).toBeLessThan(0);
            expect(comparerFromSetup(0, true, 'score')(r1, r3)).toBeGreaterThan(0);
        });
    });

    describe('Song Filtering', () => {
        test('should filter rows based on search term', () => {
            const filterInput = doc.getElementById('songFilterInput'); // Use doc
            expect(filterInput).not.toBeNull();
            const rows = doc.querySelectorAll('#songTableBody tr'); // Use doc

            filterInput.value = 'Foo';
            filterInput.dispatchEvent(new win.Event('keyup')); // Use win
            expect(rows[0].style.display).toBe('');
            expect(rows[1].style.display).toBe('none');

            filterInput.value = 'Artist Y';
            filterInput.dispatchEvent(new win.Event('keyup')); // Use win
            expect(rows[0].style.display).toBe('none');
            expect(rows[1].style.display).toBe('');

            filterInput.value = 'album';
            filterInput.dispatchEvent(new win.Event('keyup')); // Use win
            expect(rows[0].style.display).toBe('');
            expect(rows[1].style.display).toBe('');
            expect(rows[2].style.display).toBe('');

            filterInput.value = '';
            filterInput.dispatchEvent(new win.Event('keyup')); // Use win
            rows.forEach(row => expect(row.style.display).toBe(''));
        });
    });

    describe('Table Sorting', () => {
        test('should sort table by text column (Album Name) on header click', () => {
            const albumNameHeader = doc.querySelectorAll('.sortable-header')[1]; // Use doc, index is based on sortable headers only
            expect(albumNameHeader).not.toBeNull();
            const tbody = doc.getElementById('songTableBody'); // Use doc
            expect(tbody).not.toBeNull();

            albumNameHeader.click();
            let sortedRows = Array.from(tbody.querySelectorAll('tr'));
            expect(getCellValueFromSetup(sortedRows[0], 2)).toBe('Album Alpha');
            expect(getCellValueFromSetup(sortedRows[1], 2)).toBe('Album Beta');
            expect(getCellValueFromSetup(sortedRows[2], 2)).toBe('Album Gamma');
            expect(albumNameHeader.classList.contains('sorted-asc')).toBe(true);

            albumNameHeader.click();
            sortedRows = Array.from(tbody.querySelectorAll('tr'));
            expect(getCellValueFromSetup(sortedRows[0], 2)).toBe('Album Gamma');
            expect(getCellValueFromSetup(sortedRows[1], 2)).toBe('Album Beta');
            expect(getCellValueFromSetup(sortedRows[2], 2)).toBe('Album Alpha');
            expect(albumNameHeader.classList.contains('sorted-desc')).toBe(true);
        });

        test('should sort table by duration column on header click', () => {
            const durationHeader = doc.querySelectorAll('.sortable-header')[4]; // Use doc
            expect(durationHeader).not.toBeNull();
            const tbody = doc.getElementById('songTableBody'); // Use doc
            expect(tbody).not.toBeNull();

            durationHeader.click();
            let sortedRows = Array.from(tbody.querySelectorAll('tr'));
            expect(getCellValueFromSetup(sortedRows[0], 5)).toBe('N/A');
            expect(getCellValueFromSetup(sortedRows[1], 5)).toBe('0:45');
            expect(getCellValueFromSetup(sortedRows[2], 5)).toBe('3:30');

            durationHeader.click();
            sortedRows = Array.from(tbody.querySelectorAll('tr'));
            expect(getCellValueFromSetup(sortedRows[0], 5)).toBe('3:30');
            expect(getCellValueFromSetup(sortedRows[1], 5)).toBe('0:45');
            expect(getCellValueFromSetup(sortedRows[2], 5)).toBe('N/A');
        });
    });

    describe('Analyze Entire Playlist Button', () => {
        test('should call showToast on click', () => {
            const analyzeBtn = doc.getElementById('analyzePlaylistBtn'); // Use doc
            expect(analyzeBtn).not.toBeNull();
            analyzeBtn.click();
            expect(global.showToast).toHaveBeenCalledWith('Initiating analysis for playlist pl123... (Frontend Only Demo)', 'info');
        });
    });

    describe('Quick Action Buttons (Whitelist/Blacklist)', () => {
        beforeEach(() => {
            global.fetch.mockReset();
        });

        test('should call fetch and update UI on whitelist success', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true, message: 'Whitelisted!', new_status: 'whitelisted' }),
            });

            const whitelistButton = doc.querySelector('.quick-action-btn[data-song-id="s1"]'); // Use doc
            expect(whitelistButton).not.toBeNull();
            const actionCell = whitelistButton.closest('td');
            whitelistButton.click();

            await new Promise(process.nextTick);

            expect(global.fetch).toHaveBeenCalledWith('/api/song/s1/whitelist', expect.any(Object));
            expect(global.showToast).toHaveBeenCalledWith('Whitelisted!', 'success');
            expect(actionCell.innerHTML).toContain('Whitelisted');
            expect(actionCell.querySelector('button').disabled).toBe(true);
        });

        test('should call fetch and update UI on blacklist success', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true, message: 'Blacklisted!', new_status: 'blacklisted' }),
            });

            const blacklistButton = doc.querySelector('.quick-action-btn[data-song-id="s2"]'); // Use doc
            expect(blacklistButton).not.toBeNull();
            const actionCell = blacklistButton.closest('td');
            blacklistButton.click();

            await new Promise(process.nextTick);

            expect(global.fetch).toHaveBeenCalledWith('/api/song/s2/blacklist', expect.any(Object));
            expect(global.showToast).toHaveBeenCalledWith('Blacklisted!', 'success');
            expect(actionCell.innerHTML).toContain('Blacklisted');
        });

        test('should show error toast on fetch failure', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: false,
                status: 500,
                json: async () => ({ message: 'Server Error' }),
            });
            const button = doc.querySelector('.quick-action-btn[data-song-id="s1"]'); // Use doc
            expect(button).not.toBeNull();
            button.click();
            await new Promise(process.nextTick);

            expect(global.showToast).toHaveBeenCalledWith('Server Error', 'danger');
        });

        test('should show error toast if CSRF token is missing', () => {
            const csrfMeta = doc.querySelector('meta[name="csrf-token"]'); // Use doc
            expect(csrfMeta).not.toBeNull();
            csrfMeta.removeAttribute('content');

            const button = doc.querySelector('.quick-action-btn[data-song-id="s1"]'); // Use doc
            expect(button).not.toBeNull();
            button.click();
            expect(global.showToast).toHaveBeenCalledWith('Critical error: CSRF token missing. Please refresh.', 'danger');
        });
    });
});
