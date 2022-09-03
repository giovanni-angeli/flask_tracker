var tasksMilestones = []
var tasksList = null
var projectList = null
var claimList = null
var milestoneFilter = null
var projectFilter = null
var currentList = []
var currentMode = null

function formatAsPercent(num) {
  percentageNum = Intl.NumberFormat('default', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);

  if (percentageNum == 'NaN%') percentageNum = '0%'

  return percentageNum
}

let setup_global_vars = function() {
  if (tasksList == null || projectList == null || claimList == null) return;

  console.debug(tasksList)
  console.debug(projectList)
  console.debug(claimList)

}

function init_html(){

  console.debug('fetch /api/v1/task')
  fetch('/api/v1/task')
    .then((response) => response.json())
    .then((data) => {
      tasksList = data.results
      setup_global_vars()
    }).catch(err => console.error(err));

  console.debug('fetch /api/v1/task')
  fetch('/api/v1/project')
    .then((response) => response.json())
    .then((data) => {
      projectList = data.results
      setup_global_vars()
    }).catch(err => console.error(err));

  console.debug('fetch /api/v1/claim')
  fetch('/api/v1/claim')
    .then((response) => response.json())
    .then((data) => {
      claimList = data.results
      setup_global_vars()
    }).catch(err => console.error(err));

  console.log('end of init_html() ')

  // inserire un loading spinner?

}

function showTasksByStatus(){

  if (tasksList == null) return;

  // clear all select2 selections
  $('.js-example-placeholder-multiple').val(null).trigger('change');

  // TODO: better handling of currentList
  currentList = []
  currentList = tasksList.slice()
  currentMode = 'renderByStatus'
  console.log('showTasksByStatus - currentList: ',currentList)
  renderByStatus(tasksList)
}

function showClaimsByStatus(){

  if (claimList == null) return;

  // clear all select2 selections
  $('.js-example-placeholder-multiple').val(null).trigger('change');

  // TODO: better handling of currentList
  currentList = []
  currentList = claimList.slice()
  currentMode = 'renderByStatus'
  console.log('showClaimsByStatus - currentList: ',currentList)
  renderByStatus(claimList)
}

function showProjectsWorktimes(){
  if (claimList == null || tasksList == null) return;
  // alert('TBA')
  var combinatedList = tasksList.concat(claimList);
  // TODO: better handling of currentList
  currentList = []
  currentList = combinatedList.slice()
  currentMode = 'renderProjectsByWorktimes'
  renderWorkTimesByProjects(combinatedList)
}

function renderByStatus(modelList, resetFilters=true){

  if (modelList == null) return;

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


  if (milestones && projectList) {
    if ( resetFilters ) populateStatusFilters(milestones, projectList)
  }

}

function renderWorkTimesByProjects(modelList){
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

  populateStatusFilters([], projectList)
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
  // TODO: from js vanilla to jquery?
  var ctx = document.getElementById("chart-area").getContext("2d");
  if (window.statusPie){ window.statusPie.destroy() }
  window.statusPie = new Chart(ctx, config);
}

function applyFilter(){

  console.log('milestoneFilter: ',milestoneFilter)
  console.log('projectFilter: ',projectFilter)

  console.log('currentList: ',currentList)

  const filter = {
    milestone: milestoneFilter,
    project_id: projectFilter
  }
  console.log(filter)

  var filteredModelList = currentList.filter(item => {
    for (let key in filter) {
      if ( !filter[key] ){
        continue
      }
      if (item[key] === undefined || item[key] != filter[key])
        return false;
    }
    return true;
  })
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
      showProjectsWorktimes(currentList, false)
      break;
    default:
      console.log(`Sorry, we are out of ${currentMode}.`);
    }
}

$(document).ready(function () {
  //change selectboxes to selectize mode to be searchable
  $("#filter-by-milestone").select2({
    width: 'resolve', // need to override the changed default
    maximumSelectionLength: 1,
    allowClear: false
  })

  $("#filter-by-project").select2({
    width: 'resolve', // need to override the changed default
    maximumSelectionLength: 1,
    allowClear: false
  })

  $("#filter-by-milestone").on('change', function() {
    var current_val = $(this).val()[0]
    console.debug(current_val)
    milestoneFilter = current_val 
  });

  $("#filter-by-project").on('change', function() {
    var current_val = $(this).val()[0]
    console.debug(current_val)
    projectFilter = current_val
  });

});
