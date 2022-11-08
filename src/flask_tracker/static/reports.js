var tasksList = null
var projectList = null
var claimList = null
var milestoneFilterVal = null
var projectFilterVal = null
var startDateFilterValsList = null
var dueDateFilterValsList = null
var currentList = []
var currentMode = null

let pickerStartdate = null
let pickerDuedate = null

function formatAsPercent(num) {
  percentageNum = Intl.NumberFormat('default', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);

  if (percentageNum == 'NaN%') percentageNum = '0%'

  return percentageNum
}

const cleanFilters = () => {
   // clear all select2 selections
  $('.js-example-placeholder-multiple').val(null).trigger('change');

  pickerStartdate.clear()
  pickerDuedate.clear()

  $("#filters").show()
}

function showTasksByStatus(){

  if (tasksList == null || Object.keys(tasksList).length == 0) return;

  // cleanFilters()

  // TODO: better handling of currentList
  currentList = []
  currentList = tasksList.slice()
  currentMode = 'renderByStatus'
  console.log('showTasksByStatus - currentList: ',currentList)
  renderByStatus(tasksList)
}

function showClaimsByStatus(){

  if (claimList == null || Object.keys(claimList).length == 0) return;

  cleanFilters()

  // TODO: better handling of currentList
  currentList = []
  currentList = claimList.slice()
  currentMode = 'renderByStatus'
  console.log('showClaimsByStatus - currentList: ',currentList)
  renderByStatus(claimList)
}

function showProjectsWorktimes(){
  if (claimList == null ||
      tasksList == null ||
      Object.keys(claimList).length == 0 ||
      Object.keys(tasksList).length == 0) {
    return;
  }

  var combinatedList = tasksList.concat(claimList);
  // TODO: better handling of currentList
  currentList = []
  currentList = combinatedList.slice()
  currentMode = 'renderProjectsByWorktimes'
  renderWorkTimesByProjects(combinatedList)
}

function renderByStatus(modelList, resetFilters=true){

  if (modelList == null || Object.keys(modelList).length == 0) return;

  currentMode = 'renderByStatus'

  $("#table-status-tasks tbody tr").remove()
  // $("#table-results tbody tr").remove()
  $("#table-results tr").remove()
  // $("#filters").show()
  $("#wrapper-filter-milestone").show()
  // $("filters").attr("display","inline-block");

  var total = modelList.length
  var new_ = 0
  var open = 0
  var in_progress = 0
  var suspended = 0
  var test = 0
  var closed = 0
  var invalid = 0
  var milestones = []

  for (m of modelList) {
    switch (m.status){
      case "new":
        new_++
        break
      case "open":
        open++
        break
      case "in_progress":
        in_progress++
        break
      case "suspended":
        suspended++
        break
      case "test":
        test++
        break
      case "closed":
        closed++
        break
      case "invalid":
        invalid++
        break
      default:
        console.log(`Sorry, we are out of ${m.status}.`);
    }
    if (m.milestone !== undefined && !milestones.includes(m.milestone)) { 
      milestones.push(m.milestone)
    }  
  }

  var numbers = [total, new_, open, in_progress, suspended,
                      test, closed, invalid]
  const col = ['Total', 'New', 'Open', 'In progess', 'Suspended',
                    'Test', 'Closed', 'Invalid']
  for (const [i, elm] of col.entries()) {
    var table = $('#table-status-tasks')
    var tr = $('<tr>')
    var percentage = formatAsPercent(numbers[i]/total)
    tr.append('<td class="table-status-tasks-td">' + elm + '</td>')
    tr.append('<td class="table-status-tasks-td">' + numbers[i] + ' / ' + total + '</td>')
    tr.append('<td class="table-status-tasks-td">' + percentage + '</td>')
    table.find('tbody').append(tr)
  }

  var labels = col.slice(1)
  var data = numbers.slice(1)
  var colors = [
    '#26D7AE',  // new
    '#52D726',  // open
    '#FFEC00',  // in progress
    '#FF7300',  // suspended
    '#C758D0',  // test
    '#007ED6',  // closed
    '#FF0000',  // invalid
  ]
  drawPieChart(labels, data, colors)
  $("#canvas-holder").width('40%');


  if (milestones && projectList) {
    if ( resetFilters ) {
      cleanFilters()
      populateStatusFilters(milestones, projectList)
    }
  }

  if(!resetFilters) showResultsAsTable(modelList)
}

function renderWorkTimesByProjects(modelList, resetFilters=true){

  if (modelList == null || Object.keys(modelList).length == 0) return;

  $("#table-status-tasks tbody tr").remove()
  $("#table-results tr").remove()
  $("#wrapper-filter-milestone").hide()

  var wt_total = 0.0
  var wt_tasks = 0.0
  var wt_claims = 0.0
  var plannedHrs = 0.0

  for (m of modelList) {
    switch (m.type){
      case "task":
        wt_tasks += parseFloat(m.worktimes)
        if (!isNaN(parseFloat(m.planned_time))) plannedHrs += parseFloat(m.planned_time)
        break
      case "claim":
        wt_claims += parseFloat(m.worktimes_claim)
        if (!isNaN(parseFloat(m.planned_time))) plannedHrs += parseFloat(m.planned_time)
        break
      default:
        console.log(`Sorry, we are out of ${m.type}.`);
    }
  }

  wt_total = wt_tasks + wt_claims
  console.log(`Total WorkHrs: ${wt_total} - Planned Hrs: ${plannedHrs}`)
  var numbers = [wt_total, wt_tasks, wt_claims]
  const col = ['Total Worked Hours', 'Tasks Worked Hours', 'Claims Worked Hours', ]
  for (const [i, elm] of col.entries()) {
    var table = $('#table-status-tasks')
    var tr = $('<tr>')
    var percentage = formatAsPercent(numbers[i]/wt_total)
    tr.append('<td class="table-status-tasks-td">' + elm + '</td>')
    tr.append('<td class="table-status-tasks-td">' + numbers[i] + ' / ' + wt_total + '</td>')
    tr.append('<td class="table-status-tasks-td">' + percentage + '</td>')
    table.find('tbody').append(tr)
  }

  var labels = col.slice(1)
  var data = numbers.slice(1)
  var colors = [
    '#007ED6',  // task
    '#FF0000',  // claim
  ]
  drawPieChart(labels, data, colors)
  $("#canvas-holder").width('30%');

  if ( resetFilters ) {
    cleanFilters()
    populateStatusFilters([], projectList)
  }
  if(!resetFilters) {
    showResultsAsTable(modelList)
    drawBarChart([plannedHrs, wt_total])
  }
}

function populateStatusFilters(milestones, projects){
  var sortedUniqueMilestones = [...new Set(milestones)]
  var sortedUniqueProjects = [...new Set(projects)]
  $('#filter-by-milestone').empty()
  $('#filter-by-project').empty()

  for (milestone of sortedUniqueMilestones){
    $('#filter-by-milestone').append($('<option>', {
        value: milestone,
        text: milestone
    }));
  }

  for (project of sortedUniqueProjects){
    $('#filter-by-project').append($('<option>', {
        value: project.id,
        text: project.name
    }));
  }
}

function drawPieChart(labels, data, colors){
  var config = {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        label: 'Pie Chart',
        data: data,
        backgroundColor: colors,
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true
    }
  };

  var ctx = document.getElementById("chart-area").getContext("2d");
  if (window.statusPie){ window.statusPie.destroy() }
  window.statusPie = new Chart(ctx, config);
}

// TODO: check this - slow animations
function drawBarChart(data){
  var maxY = Math.max(data[0], data[1])
  var configBar = {
    type: 'bar',
    data: {
      // labels: ['Planned hrs', 'Worked hrs'],
      labels: ['hrs'],
      datasets: [{
        label: `Planned hrs: ${data[0]}`,
        data: [data[0]],
        backgroundColor: ['rgba(255, 99, 132)'],
        borderWidth: 1
      },
      {
        label: `Worked hrs: ${data[1]}`,
        data: [data[1]],
        backgroundColor: ['rgba(255, 159, 64)'],
        borderWidth: 1
      }]
    },
    options: {
      plugins: {
        legend: {
          display: true,
          labels: {
            color: 'rgb(0, 0, 0)'
          }
        },
        tooltip: {
          enabled: false // <-- this option disables tooltips
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          suggestedMax: maxY * 1.05
        }
      },
    },
  };

  var ctxBar = document.getElementById("chart-bar-area").getContext("2d");
  if (window.chartBar){ window.chartBar.destroy() }
  window.chartBar = new Chart(ctxBar, configBar);
}

function applyFilter(){

  const filters = {
    milestone: milestoneFilterVal,
    project_id: projectFilterVal,
  }
  console.log(filters)
  console.log(`startDateFilterValsList: ${startDateFilterValsList} | dueDateFilterValsList: ${dueDateFilterValsList}`)

  if (filters.milestone == null &&
      filters.project_id == null &&
      startDateFilterValsList.length == 0 &&
      dueDateFilterValsList.length == 0) {
    return
  } 


  var filteredModelList = currentList.filter(item => {
    for (let key in filters) {
      if ( !filters[key] ){
        continue
      }
      if (item[key] === undefined || item[key] != filters[key])
        return false;
    }
    return true;
  })

  if(startDateFilterValsList && startDateFilterValsList.length != 0){
    filteredModelList = filteredModelList.filter(
      elem => elem.start_date >= startDateFilterValsList[0] && elem.start_date <= startDateFilterValsList[1] )
  }
  if(dueDateFilterValsList && dueDateFilterValsList.length != 0){
    filteredModelList = filteredModelList.filter(
      elem => elem.due_date >= dueDateFilterValsList[0] && elem.due_date <= dueDateFilterValsList[1] )
  }
  console.log(filteredModelList)

  // TODO: handle empty filteredModelList on renderBy funcs
  switch (currentMode){
    case "renderByStatus":
      renderByStatus(filteredModelList, false)
      break;
    case "renderProjectsByWorktimes":
      renderWorkTimesByProjects(filteredModelList, false)
      break;
    default:
      console.log(`Sorry, we are out of ${currentMode}.`);
  }
}

function resetFilter(){

  if ( currentList == null ) return;

  switch (currentMode){
    case "renderByStatus":
      var currModelType = currentList[0].type

      if ( currModelType == "task" ) {
        renderByStatus(tasksList)
      } else {
        renderByStatus(claimList)
      }
      break;
    case "renderProjectsByWorktimes":
      if (window.chartBar){ window.chartBar.destroy() }
      renderWorkTimesByProjects(currentList)
      break;
    default:
      console.log(`Sorry, we are out of ${currentMode}.`);
    }
}

let showResultsAsTable = (modelList) => {

  if(!startDateFilterValsList && !dueDateFilterValsList && !milestoneFilterVal && !projectFilterVal) {
    return
  }

  const table = $('#table-results')

  const headers = ['Name', 'Type', 'Status', 'Project', 'Start Date',
                   'Due Date', 'Planned Time', 'Worktimes', 'Details']
  const trHead = $('<tr>')
  for (h of headers) {
    trHead.append('<th style="min-width:100px">' + h + '</th>')
  }
  table.find('thead').append(trHead)

  for (e of modelList) {
    const attrbs = [e.name, e.type, e.status, `${e.project}.${e.milestone}`,
                    e.start_date, e.due_date, e.planned_time]
    let workTime = 0
    if (Object.hasOwn(e, 'worktimes')){
      attrbs.push(e.worktimes)
      workTime = e.worktimes
    }
    if (Object.hasOwn(e, 'worktimes_claim')){
      attrbs.push(e.worktimes_claim)
      workTime = e.worktimes_claim
    }
    const tr = $('<tr>')
    const lastElementIndex = attrbs.length - 1;
    for (const [i, a] of Object.entries(attrbs)) {
      let tdStartTag = '<td>'
      if (i == lastElementIndex && e.planned_time > 0){
        if (workTime <= e.planned_time) {
          tdStartTag = '<td class="worktime-ok">'
        } else {
          tdStartTag = '<td class="worktime-ko">'
        }
      }
      tr.append(`${tdStartTag}${a}</td>`)
    }
    tr.append(`<td><a href="/${e.type}/details/?id=${e.id}&url=%2F${e.type}%2F" target="_blank" rel="noopener noreferrer">Details</a></td>`)
    table.find('tbody').append(tr)
  }
}

const setIsLoading = function (isLoading) {
    if (isLoading) {
        document.getElementById('loading-container').classList.add('is-visible');
        return;
    }
    document.getElementById('loading-container').classList.remove('is-visible');
};

const fetchRequests = () => {

  const fetchReqTask = fetch(
    "/api/v1/task"
  ).then((res) => res.json())
  .catch(err => console.error(err));

  const fetchReqProject = fetch(
    `/api/v1/project`
  ).then((res) => res.json());

  const fetchReqClaim = fetch(
    `/api/v1/claim`
  ).then((res) => res.json());

  // do fetch requests in parallel using the Promise.all() method
  const responses = Promise.all([fetchReqTask, fetchReqProject, fetchReqClaim]);

  return responses
}

// https://developer.mozilla.org/en-US/docs/Web/API/Window/DOMContentLoaded_event
window.addEventListener('DOMContentLoaded', function initApp() {

  setIsLoading(true);

  let select2Dict = {
    width: 'resolve', // need to override the changed default
    maximumSelectionLength: 1,
    allowClear: false
  }
  const milestoneFilter = $("#filter-by-milestone").select2(select2Dict)
  const projectFilter = $("#filter-by-project").select2(select2Dict)
  
  easepickDictBase = {
    element: "",
    css: [easepickCssUrl],
    zIndex: 10,
    grid: 2,
    calendars: 2,
    autoApply: true,
    AmpPlugin: {
        dropdown: {
            months: true,
            years: true,
            minYear: 2017
        },
        resetButton: true
    },
    PresetPlugin: {
        position: "bottom"
    },
    plugins: [
        "AmpPlugin",
        "RangePlugin",
        "PresetPlugin"
    ],
  }
  const easepickDictStartDate = JSON.parse(JSON.stringify(easepickDictBase)); // deep copy
  const easepickDictDueDate = JSON.parse(JSON.stringify(easepickDictBase));   // deep copy
  easepickDictDueDate.element = '#datepicker-duedate'
  easepickDictStartDate.element = '#datepicker-startdate'
  pickerStartdate = new easepick.create(easepickDictStartDate)
  pickerDuedate = new easepick.create(easepickDictDueDate)

  // jquery event handlers
  milestoneFilter.on('change', function() {
    var current_val = $(this).val()[0]
    console.debug("filter-by-milestone val: ", current_val)
    milestoneFilterVal = current_val 
  });
  projectFilter.on('change', function() {
    var current_val = $(this).val()[0]
    console.debug("filter-by-project val: ", current_val)
    projectFilterVal = current_val
  });
  pickerStartdate.on('select', (evt) => {
    // an object destructuring assignment. See https://mzl.la/3x6nnOQ
    const { start, end } = evt.detail;
    if (start instanceof Date && end instanceof Date) {
      console.debug(start.format('YYYY-MM-DD'))
      console.debug(end.format('YYYY-MM-DD'))
      startDateFilterValsList = [start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD')]
    }
  })
  pickerStartdate.on('clear', (e) => {
    startDateFilterValsList = null
  });
  pickerDuedate.on('select', (evt) => {
    // an object destructuring assignment. See https://mzl.la/3x6nnOQ
    const { start, end } = evt.detail;
    if (start instanceof Date && end instanceof Date) {
      console.debug(start.format('YYYY-MM-DD'))
      console.debug(end.format('YYYY-MM-DD'))
      dueDateFilterValsList = [start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD')]
    }
  })
  pickerDuedate.on('clear', (e) => {
    dueDateFilterValsList = null
  });

  const allData = fetchRequests()
  allData.then(
    (fetchData) => {
      tasksList = fetchData[0].results
      projectList = fetchData[1].results
      claimList = fetchData[2].results
    }
  ).catch(err => { console.error(err) })
  .finally(() => { setIsLoading(false); });

});