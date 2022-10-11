var tasksList = null
var projectList = null
var claimList = null
var milestoneFilterVal = null
var projectFilterVal = null
var startDateFilter = null
var dueDateFilter = null
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
}

function showTasksByStatus(){

  if (tasksList == null) return;

  cleanFilters()

  // TODO: better handling of currentList
  currentList = []
  currentList = tasksList.slice()
  currentMode = 'renderByStatus'
  console.log('showTasksByStatus - currentList: ',currentList)
  renderByStatus(tasksList)
}

function showClaimsByStatus(){

  if (claimList == null) return;

  cleanFilters()

  // TODO: better handling of currentList
  currentList = []
  currentList = claimList.slice()
  currentMode = 'renderByStatus'
  console.log('showClaimsByStatus - currentList: ',currentList)
  renderByStatus(claimList)
}

function showProjectsWorktimes(){
  if (claimList == null || tasksList == null) return;

  cleanFilters()

  var combinatedList = tasksList.concat(claimList);
  // TODO: better handling of currentList
  currentList = []
  currentList = combinatedList.slice()
  currentMode = 'renderProjectsByWorktimes'
  renderWorkTimesByProjects(combinatedList)
}

function renderByStatus(modelList, resetFilters=true){

  if (modelList == null) return;

  currentMode = 'renderByStatus'

  $("#table-status-tasks tbody tr").remove()
  $("#filters").show()
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
    if ( resetFilters ) populateStatusFilters(milestones, projectList)
  }
}

function renderWorkTimesByProjects(modelList, resetFilters=true){
  $("#table-status-tasks tbody tr").remove()
  $("#filters").show()
  $("#wrapper-filter-milestone").hide()

  console.log('[renderWorkTimesByProjects] modelList: ',modelList)

  var wt_total = 0.0
  var wt_tasks = 0.0
  var wt_claims = 0.0

  for (m of modelList) {
    switch (m.type){
      case "task":
        wt_tasks += parseFloat(m.worktimes)
        break
      case "claim":
        wt_claims += parseFloat(m.worktimes_claim)
        break
      default:
        console.log(`Sorry, we are out of ${m.type}.`);
    }
  }

  wt_total = wt_tasks + wt_claims
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

  if ( resetFilters ) populateStatusFilters([], projectList)
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

function applyFilter(){

  const filters = {
    milestone: milestoneFilterVal,
    project_id: projectFilterVal,
  }
  console.log(filters)
  console.log(`startDateFilter: ${startDateFilter} | dueDateFilter: ${dueDateFilter}`)

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

  if(startDateFilter && startDateFilter.length != 0){
    filteredModelList = filteredModelList.filter(
      elem => elem.start_date >= startDateFilter[0] && elem.start_date <= startDateFilter[0] )
  }
  if(dueDateFilter && dueDateFilter.length != 0){
    filteredModelList = filteredModelList.filter(
      elem => elem.due_date >= dueDateFilter[0] && elem.due_date <= dueDateFilter[0] )
  }
  console.log(filteredModelList)

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
      console.log('currModelType > ',currModelType)

      if ( currModelType == "task" ) {
        showTasksByStatus()
      } else {
        showClaimsByStatus()
      }
      break;
    case "renderProjectsByWorktimes":
      showProjectsWorktimes(currentList)
      break;
    default:
      console.log(`Sorry, we are out of ${currentMode}.`);
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
      startDateFilter = [start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD')]
    }
  })
  pickerStartdate.on('clear', (e) => {
    startDateFilter = null
  });
  pickerDuedate.on('select', (evt) => {
    // an object destructuring assignment. See https://mzl.la/3x6nnOQ
    const { start, end } = evt.detail;
    if (start instanceof Date && end instanceof Date) {
      console.debug(start.format('YYYY-MM-DD'))
      console.debug(end.format('YYYY-MM-DD'))
      dueDateFilter = [start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD')]
    }
  })
  pickerDuedate.on('clear', (e) => {
    dueDateFilter = null
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