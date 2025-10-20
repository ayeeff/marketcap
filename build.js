const fs = require('fs');
const Papa = require('papaparse');
const fetch = require('node-fetch');

async function build() {
  try {
    console.log('Starting build...');
    const base = 'https://raw.githubusercontent.com/ayeeff/marketcap/main/data/';

    // Fetch and parse Companies
    const companiesResp = await fetch(base + 'empire_top_companies.csv');
    if (!companiesResp.ok) throw new Error(`Failed to fetch companies: ${companiesResp.status}`);
    const companiesText = await companiesResp.text();
    const companiesParsed = Papa.parse(companiesText, { header: true, skipEmptyLines: true, dynamicTyping: false });
    const companies = companiesParsed.data.map(row => {
      const companyName = (row.Company || '').split('\n')[0].trim();
      const ticker = (row.Company || '').split('\n')[1]?.trim() || '';
      return {
        empire: parseInt(row.Empire),
        name: companyName,
        ticker: ticker,
        marketCap: row['Market Cap'] || row.Market_Cap || '',
        country: row.Country || row.country || row.CountryCode || row.Country_Code || ''
      };
    }).filter(c => !isNaN(c.empire));  // Filter invalid rows

    // Fetch and parse Institutions (Research)
    const researchResp = await fetch(base + 'empire_research.csv');
    if (!researchResp.ok) throw new Error(`Failed to fetch research: ${researchResp.status}`);
    const researchText = await researchResp.text();
    const researchParsed = Papa.parse(researchText, { header: true, skipEmptyLines: true, dynamicTyping: true });
    const institutions = researchParsed.data.map(row => ({
      empire: parseInt(row.Empire),
      rank: parseInt(row.Empire_Rank),
      name: row.Institution,
      globalRank: parseInt(row.Global_Rank) || null,
      researchShare: parseFloat(row['Research Share']) || 0,
      country: row.Country || row.country || row.CountryCode || row.Country_Code || ''
    })).filter(i => !isNaN(i.empire));

    // Fetch and parse Market Cap Totals
    const marketCapResp = await fetch(base + 'empire_totals.csv');
    if (!marketCapResp.ok) throw new Error(`Failed to fetch market totals: ${marketCapResp.status}`);
    const marketCapText = await marketCapResp.text();
    const marketCapParsed = Papa.parse(marketCapText, { header: true, skipEmptyLines: true, dynamicTyping: false });
    const marketCapTotals = marketCapParsed.data.map(row => ({ 
      empire: parseInt(row.Empire), 
      total: row['Total Market Cap'], 
      share: row.Share,
      date: row.Date 
    })).filter(m => !isNaN(m.empire));

    // Fetch and parse R&D (Nature Share)
    const rdResp = await fetch(base + 'empire_nature_share.csv');
    if (!rdResp.ok) throw new Error(`Failed to fetch R&D: ${rdResp.status}`);
    const rdText = await rdResp.text();
    const rdParsed = Papa.parse(rdText, { header: true, skipEmptyLines: true, dynamicTyping: true });
    const rdExpenditures = rdParsed.data.map(row => ({ 
      empire: parseInt(row.empire), 
      share: parseFloat(row.share_2024), 
      percent: parseFloat(row.percent) 
    })).filter(r => !isNaN(r.empire));

    // Fetch and parse GDP
    const gdpResp = await fetch(base + 'empire_gdp_ppp_2025.csv');
    if (!gdpResp.ok) throw new Error(`Failed to fetch GDP: ${gdpResp.status}`);
    const gdpText = await gdpResp.text();
    const gdpParsed = Papa.parse(gdpText, { header: true, skipEmptyLines: true, dynamicTyping: true });
    const gdpData = gdpParsed.data.map(row => ({ 
      empire: parseFloat(row['empire#']), 
      total: parseFloat(row.total), 
      percent: parseFloat(row['%']) 
    })).filter(g => !isNaN(g.empire));

    // Fetch and parse Cities
    const citiesResp = await fetch(base + 'empire_cities_population.csv');
    if (!citiesResp.ok) throw new Error(`Failed to fetch cities: ${citiesResp.status}`);
    const citiesText = await citiesResp.text();
    const citiesParsed = Papa.parse(citiesText, { header: true, skipEmptyLines: true, dynamicTyping: true });
    const citiesData = citiesParsed.data.map(row => ({ 
      empire: parseInt(row.Empire), 
      rank: parseInt(row.Rank), 
      city: row.City, 
      country: row.Country, 
      population: parseInt(row.Population), 
      date: row.Scraped_Date 
    })).filter(c => !isNaN(c.empire));

    // Embed data
    const embeddedData = { 
      companies, 
      institutions, 
      marketCapTotals, 
      rdExpenditures, 
      gdpData, 
      citiesData, 
      lastUpdated: new Date().toISOString() 
    };

    // Read input HTML and replace placeholder
    const html = fs.readFileSync('input.html', 'utf8');
    const output = html.replace('<!-- EMBED_DATA -->', `var embeddedData = ${JSON.stringify(embeddedData)};`);
    fs.writeFileSync('cached-dashboard.html', output);

    console.log('Build complete! Generated cached-dashboard.html');
  } catch (error) {
    console.error('Build failed:', error);
    process.exit(1);
  }
}

build();
