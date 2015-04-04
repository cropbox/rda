library(reshape2)
library(ggplot2)
library(grid)
library(gridExtra)
library(scales)

##################
# load functions #
##################

load_multi <- function(name) {
  filename <- paste(name, '_multi.csv', sep='')
  read.csv(filename)
}

load_single <- function(name, mdf) {
  filename <- paste(name, '.csv', sep='')
  sdf <- read.csv(filename, na.strings=c(''))
  for (c in colnames(sdf)[-1]) {
    sdf[,c] <- sapply(as.Date(sdf[,c]), yday)
  }
  sdf <- melt(sdf, id.vars=c('year'), variable.name='model', value.name='day', na.rm=TRUE)
  sdf$model <- factor(sdf$model, levels=levels(mdf$model))
  sdf
}

transform_diff <- function(df) {
  years <- subset(df, model == 'Obs')$year
  df <- subset(df, year %in% years)
  for (y in years) {
    df$day[df$year == y] <- subset(df, year == y)$day - subset(df, model == 'Obs' & year == y)$day
  }
  df
}

extract_obs <- function(df) {
  subset(df, model == 'Obs')
}

remove_obs <- function(df) {
  df[df$model != 'Obs',]
}

load <- function(name, diff=TRUE, start_year=NULL, end_year=NULL) {
  mdf <- load_multi(name)
  sdf <- load_single(name, mdf)
  if (diff) {
    mdf <- transform_diff(mdf)
    sdf <- transform_diff(sdf)
  }
  if (!is.null(start_year)) {
    mdf <- subset(mdf, year >= start_year)
    sdf <- subset(sdf, year >= start_year)
  }
  if (!is.null(end_year)) {
    mdf <- subset(mdf, year <= end_year)
    sdf <- subset(sdf, year <= end_year)
  }
  obs <- extract_obs(sdf)
  mdf <- remove_obs(mdf)
  sdf <- remove_obs(sdf)
  list(mdf=mdf, sdf=sdf, obs=obs)
}

##################
# plot functions #
##################

plot_individual <- function(df, name=NULL, width=16, height=4) {
  p <- ggplot(data=df$mdf, aes(x=factor(year), y=day, ymax=max(day), colour=model, fill=model)) +
    ggtitle('Multi-model multi-parameter prediction') +
    geom_line(data=df$obs, aes(group=1)) +
    #geom_jitter(aes(size=count), position=position_jitter(width=1), alpha=.7) +
    #geom_point(aes(size=count), position=position_jitterdodge(dodge.width=.5), alpha=.5) +
    geom_point(aes(size=count), position=position_dodge(width=.5), alpha=.5) +
    geom_boxplot(width=.5, position=position_dodge(width=.5), fill=NA) +
    geom_point(data=df$sdf, position=position_dodge(width=.5), shape=8, size=3, alpha=1) +
    scale_x_discrete(name='year', breaks=pretty_breaks()) +
    theme(
      legend.position='bottom'
    )
  
  if (!is.null(name)) {
    ggsave(paste(name, '_individual.pdf', sep=''), width=width, height=height)
  }
  p
}

plot_median <- function(df, name=NULL, width=16, height=4) {
  p <- ggplot(data=df$mdf, aes(x=year, y=day, colour=model)) +
    ggtitle('Multi-model multi-parameter prediction') +
    geom_line(data=df$obs) +
    #stat_summary(fun.data='median_hilow', aes(colour=''))
    geom_boxplot(aes(group=factor(year), colour='Median'), width=.5, alpha=.3) +
    #scale_x_continuous(breaks=unique(df$mdf$year)) +
    scale_x_continuous(breaks=pretty_breaks()) +
    theme(
      legend.position='none'
    )
  
  if (!is.null(name)) {
    ggsave(paste(name, '_median.pdf', sep=''), width=width, height=height)
  }
  p
}

plot_combinations <- function(df, name=NULL, width=16, height=4) {
  mdf <- df$mdf
  M <- levels(mdf$model)
  M <- M[M != 'Obs']
  N <- length(M)
  #plots <- vector('list', sum(sapply(seq(N), function (k) choose(N, k))))
  for (n in rev(seq(N))) {
    models <- combn(M, n)
    nmodels <- ncol(models)
    plots <- vector('list', nmodels)
    for (i in seq(nmodels)) {
      ndf <- list(mdf=subset(mdf, model %in% c(models[,i], 'Obs')), obs=df$obs)
      p <- plot_median(ndf) +
        ggtitle(paste(n, i, paste(models[,i], collapse=','))) +
        ylim(min(mdf$day), max(mdf$day))
      #print(p)
      plots[[i]] <- p
    }
    do.call(grid.arrange, c(plots, ncol=1))
    
    if (!is.null(name)) {
      filename <- paste(name, '_combinations_', n, '_.pdf', sep='')
      p <- do.call(arrangeGrob, c(plots, ncol=1))
      ggsave(filename, p, width=width, height=height*nmodels, limitsize=FALSE)
    }
  }
}

#####################
# output generation #
#####################

save <- function(name, diff=TRUE, start_year=NULL, end_year=NULL, width=16, height=4) {
  df <- load(name, diff, start_year, end_year)
  plot_individual(df, name, width, height)
  plot_median(df, name, width, height)
  plot_combinations(df, name, width, height)
}

#######
# run #
#######

save('apple_fuji')
save('apple_honeycrisp')
save('cherry_yoshino', width=40, height=8)
save('cherry_kwanzan', width=40, height=8)
save('cherry_yoshino', start_year=1990, width=40, height=8)
save('cherry_kwanzan', start_year=1990, width=40, height=8)